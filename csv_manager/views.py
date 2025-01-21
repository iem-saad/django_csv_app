from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from .models import UploadedCSV, DerivedCSV, CSVChanges
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from mimetypes import guess_type
from datetime import datetime
from .tasks import process_csv, apply_csv_changes
import csv
import json
import io


def home(request):
    """
    Render the homepage with the CSV upload form.
    """
    return render(request, 'csv_manager/home.html', {'is_home': True})

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

        decoded_file = file.read().decode('utf-8')

        # Save the parsed data to the database
        uploaded_csv = UploadedCSV.objects.create(name=name, content=json.dumps(decoded_file))

        messages.success(
            request, 
            "Your CSV has been uploaded and is being processed. It will be ready to view shortly.",
            extra_tags='success'
        )
        
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

def view_csv(request, csv_id, is_derived=False):
    """
    Render the contents of an UploadedCSV or DerivedCSV in a table.
    """
    if is_derived:
        csv_entry = get_object_or_404(DerivedCSV, id=csv_id)
    else:
        csv_entry = get_object_or_404(UploadedCSV, id=csv_id)

    return render(request, 'csv_manager/view_csv.html', {'csv_entry': csv_entry})

def add_data_to_csv(request, csv_id):
    """
    Unified function to add data to either an UploadedCSV or a DerivedCSV.
    """
    is_derived = request.GET.get('is_derived', '0') == '1'
    if is_derived:
        csv_entry = get_object_or_404(DerivedCSV, id=csv_id)
        schema = csv_entry.parent.schema
    else:
        csv_entry = get_object_or_404(UploadedCSV, id=csv_id)
        schema = csv_entry.schema

    if request.method == "POST":
        field_names = list(schema.keys())
        adjusted_field_names = [f"{field}[]" for field in field_names]
        num_rows = len(request.POST.getlist(adjusted_field_names[0]))  # Use adjusted field names
        new_rows = []

        for i in range(num_rows):
            new_row = {}
            for key, data_type in schema.items():
                value = request.POST.getlist(f"{key}[]")[i]  # Use adjusted field names
                try:
                    if data_type == "integer":
                        value = int(value)
                    elif data_type == "float":
                        value = float(value)
                    elif data_type == "datetime":
                        value = value.replace("T", " ")
                        if len(value.split(":")) == 2:  # If seconds are missing
                            value += ":00"
                        value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
                    elif data_type == "date":
                        value = datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
                    else:
                        value = str(value)
                    new_row[key] = value
                except ValueError as e:
                    messages.error(request, f"Invalid value '{value}' for {key} in row {i + 1}: {e}", extra_tags='warning')
                    return render(request, "csv_manager/add_data_csv.html", {"csv_entry": csv_entry, "schema": schema})

            new_rows.append(new_row)

        csv_changes = CSVChanges.objects.create(
            content_type=ContentType.objects.get_for_model(csv_entry),
            object_id=csv_entry.id,
            data=new_rows
        )

        apply_csv_changes.delay(csv_changes.id)
        messages.success(request, f"Successfully added {len(new_rows)} rows!")
        return redirect("my_csvs")

    return render(request, "csv_manager/add_data_csv.html", {"csv_entry": csv_entry, "schema": schema, "is_derived": is_derived})

def visualize_csv(request, csv_id):
    """
    View to visualize either an UploadedCSV or a DerivedCSV.
    """
    is_derived = request.GET.get('is_derived', '0') == '1'
    if is_derived:
        csv_entry = get_object_or_404(DerivedCSV, id=csv_id)
        content = csv_entry.content
        schema = csv_entry.parent.schema
    else:
        csv_entry = get_object_or_404(UploadedCSV, id=csv_id)
        content = csv_entry.content
        schema = csv_entry.schema

    # Slice content to last 400 records for better view
    content = content[-400:] if len(content) > 400 else content

    allowed_columns = {col: col_type for col, col_type in schema.items() if col_type != 'string'}

    return render(request, 'csv_manager/visualize_csv.html', {
        'csv_entry': csv_entry,
        'content': content,
        'schema': schema,
        'allowed_columns': allowed_columns,
        'is_derived': is_derived
    })

def my_changes(request):
    """
    View to display all changes recorded in the CSVChanges table.
    """
    changes = CSVChanges.objects.all().order_by('-id')

    # Add a derived flag to each change
    for change in changes:
        change.is_derived = change.content_type.model == 'derivedcsv'

    return render(request, 'csv_manager/my_changes.html', {'changes': changes})