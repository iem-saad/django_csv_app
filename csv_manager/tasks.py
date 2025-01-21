import csv
import io
import re
from celery import shared_task
from .models import UploadedCSV, DerivedCSV, CSVChanges
from datetime import datetime
from django.contrib.contenttypes.models import ContentType
import copy
import json
from .utils import send_csv_email
import pandas as pd
from io import StringIO


@shared_task
def process_csv(uploaded_csv_id):
    """
    Celery task to process the uploaded CSV:
    Normalize headers, infer schema using pandas with datetime detection, and save as a DerivedCSV.
    """
    try:
        uploaded_csv = UploadedCSV.objects.get(id=uploaded_csv_id)
        uploaded_csv.status = 'processing'
        uploaded_csv.save()

        raw_csv = json.loads(uploaded_csv.content)  # Load raw CSV string stored as JSON

        # Load the raw CSV into pandas DataFrame
        df = pd.read_csv(StringIO(raw_csv))

        # Normalize column headers
        df.columns = [re.sub(r'[^\w\s]', '', col).strip().replace(' ', '_').lower() for col in df.columns]

        # Infer schema using pandas with datetime detection
        schema = infer_schema_with_pandas(df)

        # Normalize data based on inferred schema
        for column, col_type in schema.items():
            if col_type == "datetime":
                df[column] = pd.to_datetime(df[column], format="%Y-%m-%d %H:%M:%S", errors="coerce")
                df[column] = df[column].dt.strftime("%Y-%m-%d %H:%M:%S")  # Convert datetime to string
            elif col_type == "date":
                df[column] = pd.to_datetime(df[column], format="%Y-%m-%d", errors="coerce").dt.date
                df[column] = df[column].astype(str)  # Convert date to string for JSON serialization

        normalized_data = df.to_dict(orient="records")

        # Save normalized data and schema
        uploaded_csv.schema = schema
        uploaded_csv.content = normalized_data
        uploaded_csv.save()

        # Process the data (e.g., divide integers/floats)
        processed_data = []
        for row in normalized_data:
            processed_row = {}
            for key, value in row.items():
                if schema[key] == "integer" and pd.notna(value):
                    processed_row[key] = int(value) // 2
                elif schema[key] == "float" and pd.notna(value):
                    processed_row[key] = float(value) / 2
                else:
                    processed_row[key] = value
            processed_data.append(processed_row)

        # Create a DerivedCSV entry
        DerivedCSV.objects.create(parent=uploaded_csv, content=processed_data)

        # Mark the uploaded CSV as processed
        uploaded_csv.status = 'processed'
        uploaded_csv.save()

    except UploadedCSV.DoesNotExist:
        print(f"UploadedCSV with ID {uploaded_csv_id} does not exist.")
    except Exception as e:
        error_message = str(e)
        uploaded_csv.status = 'failed_processing'
        uploaded_csv.failure_reason = error_message
        uploaded_csv.save()
        print(f"Error processing CSV: {error_message}")

def infer_schema_with_pandas(df):
    """
    Infer the schema of a pandas DataFrame, including datetime detection.
    Returns a dictionary with column names as keys and data types as values.
    """
    dtype_mapping = {
        "int64": "integer",
        "float64": "float",
        "object": "string",
    }

    schema = {}
    for column in df.columns:
        dtype = str(df[column].dtypes)

        # Check if column is datetime-like
        if dtype == "object":  # Likely a string column
            try:
                pd.to_datetime(df[column], format="%Y-%m-%d %H:%M:%S", errors="raise")
                schema[column] = "datetime"
                continue
            except ValueError:
                try:
                    pd.to_datetime(df[column], format="%Y-%m-%d", errors="raise")
                    schema[column] = "date"
                    continue
                except ValueError:
                    pass  # If both fail, fallback to string

        # Map the dtype using the standard mapping
        schema[column] = dtype_mapping.get(dtype, "string")  # Default to "string"

    return schema

# This function is not used for now.
def infer_schema(csv_content):
    """
    Infer the schema of a CSV file based on its content.
    Returns a dictionary with column names as keys and data types as values.
    """
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)

    if not rows:
        return {}

    # Extract header (column names)
    header = rows[0]
    schema = {col: None for col in header}

    # Analyze rows to infer data types
    for row in rows[1:]:
        for col, value in zip(header, row):
            value = value.strip()  # Trim whitespace
            if value:  # Ignore empty values
                inferred_type = "string"
                try:
                    int(value)
                    inferred_type = "integer"
                except ValueError:
                    try:
                        float(value)
                        inferred_type = "float"
                    except ValueError:
                        try:
                            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")  # Adjust format as needed
                            inferred_type = "datetime"
                        except ValueError:
                            try:
                                datetime.strptime(value, "%Y-%m-%d")
                                inferred_type = "date"
                            except ValueError:
                                inferred_type = "string"  # Fallback

                # Update schema if it's not set or needs broadening
                if schema[col] is None:
                    schema[col] = inferred_type
                elif schema[col] != inferred_type:
                    schema[col] = "string"

    for col in schema:
        if schema[col] is None:
            schema[col] = "string"

    return schema

@shared_task
def test_celery_task(x, y):
    return x + y

@shared_task
def apply_csv_changes(changes_id):
    """
    Background job to apply changes from CSVChanges to the associated UploadedCSV or DerivedCSV.
    Creates a new DerivedCSV with the updated content.
    """
    try:
        csv_changes = CSVChanges.objects.get(id=changes_id)
        associated_csv = csv_changes.csv_entry
        original_content = associated_csv.content

        updated_content = copy.deepcopy(original_content)

        for row in csv_changes.data:
            updated_content.append(row)

        DerivedCSV.objects.create(
            parent=associated_csv if isinstance(associated_csv, UploadedCSV) else associated_csv.parent,
            content=updated_content
        )

        csv_changes.status = "processed"
        csv_changes.save()

        return f"CSVChanges {changes_id} applied successfully and new DerivedCSV created."
    except CSVChanges.DoesNotExist:
        return f"CSVChanges with ID {changes_id} does not exist."
    except Exception as e:
        return f"Error applying CSVChanges {changes_id}: {e}"


def retry_failed_and_unprocessed_csvs():
    """
    Celery task to retry processing CSVs with 'unprocessed' or 'failed_processing' status.
    """
    try:
        csvs_to_retry = UploadedCSV.objects.filter(status__in=['unprocessed', 'failed_processing'])
        
        for csv in csvs_to_retry:
            print(f"Retrying processing for CSV: {csv.id} - {csv.name}")
            process_csv.delay(csv.id)
    except Exception as e:
        print(f"Error retrying failed and unprocessed CSVs: {e}")