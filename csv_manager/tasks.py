from celery import shared_task
from .models import UploadedCSV, DerivedCSV

@shared_task
def process_csv(uploaded_csv_id):
    """
    Celery task to process the uploaded CSV:
    Divide all integer columns by 2 and save as a DerivedCSV.
    """
    try:
        uploaded_csv = UploadedCSV.objects.get(id=uploaded_csv_id)
        original_data = uploaded_csv.content

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


@shared_task
def test_celery_task(x, y):
    return x + y