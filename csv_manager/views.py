from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from .models import UploadedCSV, DerivedCSV
from django.contrib import messages
from mimetypes import guess_type
from .tasks import process_csv
import csv
import io


def home(request):
    """
    Render the homepage with the CSV upload form.
    """
    return render(request, 'csv_manager/home.html')

def my_csvs(request):
    """
    Display all uploaded CSVs with their upload times.
    """
    csvs = UploadedCSV.objects.all()
    return render(request, 'csv_manager/my_csvs.html', {'csvs': csvs})

def upload_csv(request):
    """
    View to handle file uploads, parse the CSV, and save it to the database.
    """
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        name = file.name

        if not name.endswith('.csv') or guess_type(name)[0] != 'text/csv':
            messages.error(request, "Invalid file type. Please upload a valid CSV file.", extra_tags='warning')
            return redirect('home')

        csv_data = []
        decoded_file = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded_file))
        for row in reader:
            csv_data.append(row)

        # Save the parsed data to the database
        uploaded_csv = UploadedCSV.objects.create(name=name, content=csv_data)
        # Trigger the Celery task to process the CSV
        process_csv.delay(uploaded_csv.id)

        return redirect('my_csvs')

    return render(request, 'csv_manager/home.html')

def download_csv(request, csv_id, is_derived=False):
    """
    Download an UploadedCSV or DerivedCSV as a CSV file.
    """
    try:
        if is_derived:
            csv_entry = DerivedCSV.objects.get(id=csv_id)
            file_name = f"{csv_entry.parent.name.split('.')[0]}-derived-{csv_id}.csv"
        else:
            csv_entry = UploadedCSV.objects.get(id=csv_id)
            file_name = csv_entry.name

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'

        writer = csv.writer(response)
        content = csv_entry.content
        if content:
            keys = content[0].keys()
            writer.writerow(keys)
            for row in content:
                writer.writerow(row.values())

        return response
    except (UploadedCSV.DoesNotExist, DerivedCSV.DoesNotExist):
        return HttpResponse("CSV not found.", status=404)

def delete_csv(request, csv_id, is_derived=False):
    """
    Delete an UploadedCSV or a DerivedCSV.
    If an UploadedCSV is deleted, all its DerivedCSV children are also deleted.
    """
    try:
        if is_derived:
            derived_csv = get_object_or_404(DerivedCSV, id=csv_id)
            derived_csv.delete()
            return JsonResponse({'status': 'success', 'message': 'Derived CSV deleted successfully.'})
        else:
            uploaded_csv = get_object_or_404(UploadedCSV, id=csv_id)
            uploaded_csv.delete()
            return JsonResponse({'status': 'success', 'message': 'Uploaded CSV and its derived CSVs deleted successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)