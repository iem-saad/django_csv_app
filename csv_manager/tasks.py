import csv
import io
from celery import shared_task
from .models import UploadedCSV, DerivedCSV
from datetime import datetime

@shared_task
def process_csv(uploaded_csv_id):
    """
    Celery task to process the uploaded CSV:
    Divide all integer columns by 2 and save as a DerivedCSV.
    """
    try:
        uploaded_csv = UploadedCSV.objects.get(id=uploaded_csv_id)
        original_data = uploaded_csv.content

        # Extract schema
        csv_content = "\n".join(
            [",".join(original_data[0].keys())] + 
            [",".join(str(value) for value in row.values()) for row in original_data]
        )

        schema = infer_schema(csv_content)
        print(schema)

        # Update the UploadedCSV with the schema
        uploaded_csv.schema = schema
        uploaded_csv.save()

        processed_data = []
        for row in original_data:
            processed_row = {}
            for key, value in row.items():
                if value.isdigit():
                    processed_row[key] = int(value) // 2
                else:
                    processed_row[key] = value
            processed_data.append(processed_row)

        DerivedCSV.objects.create(parent=uploaded_csv, content=processed_data)

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