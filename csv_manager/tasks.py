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

@shared_task
def process_csv(uploaded_csv_id):
    """
    Celery task to process the uploaded CSV:
    Normalize headers, infer schema, process integer columns, and save as a DerivedCSV.
    """
    try:
        uploaded_csv = UploadedCSV.objects.get(id=uploaded_csv_id)
        raw_csv = json.loads(uploaded_csv.content)  # Load raw CSV string stored as JSON

        reader = csv.reader(io.StringIO(raw_csv))
        rows = list(reader)

        headers = rows[0]
        normalized_headers = [
            re.sub(r'[^\w\s]', '', col).strip().replace(' ', '_').lower() for col in headers
        ]

        normalized_data = []
        for row in rows[1:]:
            normalized_data.append(dict(zip(normalized_headers, row)))

        csv_content = "\n".join(
            [",".join(normalized_headers)] +
            [",".join(str(value) for value in row.values()) for row in normalized_data]
        )
        schema = infer_schema(csv_content)

        uploaded_csv.schema = schema
        uploaded_csv.content = normalized_data
        uploaded_csv.save()

        processed_data = []
        for row in normalized_data:
            processed_row = {}
            for key, value in row.items():
                if schema[key] == "integer" and value.isdigit():
                    processed_row[key] = int(value) // 2
                else:
                    processed_row[key] = value
            processed_data.append(processed_row)

        DerivedCSV.objects.create(parent=uploaded_csv, content=processed_data)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=normalized_headers)
        writer.writeheader()
        writer.writerows(processed_data)
        csv_attachment = output.getvalue()

        subject = "Your Processed CSV is Ready!"
        message = "The CSV you uploaded has been successfully processed. Please find the filtered CSV attached."
        send_csv_email('testuser@gmail.com', subject, message, csv_attachment)

        uploaded_csv.status = 'processed'
        uploaded_csv.save()

    except UploadedCSV.DoesNotExist:
        print(f"UploadedCSV with ID {uploaded_csv_id} does not exist.")
    except Exception as e:
        print(f"Error processing CSV: {e}")


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
            if value.strip():  # Ignore empty values
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
                            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")  # Adjust the format as needed
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

