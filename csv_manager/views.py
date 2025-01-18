from django.shortcuts import render
from django.http import JsonResponse
from .models import UploadedCSV
from .tasks import process_csv
import csv
import io

def upload_csv(request):
    """
    View to handle file uploads, parse the CSV, and save it to the database.
    """
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        name = file.name

        csv_data = []
        decoded_file = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded_file))
        for row in reader:
            csv_data.append(row)

        # Save the parsed data to the database
        uploaded_csv = UploadedCSV.objects.create(name=name, content=csv_data)
        # Trigger the Celery task to process the CSV
        process_csv.delay(uploaded_csv.id)

        return JsonResponse({'status': 'success', 'message': f'File {name} uploaded successfully!', 'id': uploaded_csv.id})

    return render(request, 'csv_manager/upload_csv.html')