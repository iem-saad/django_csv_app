from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class UploadedCSV(models.Model):
    """
    Model to represent the original uploaded CSV file.
    """
    STATUS_CHOICES = [
        ('unprocessed', 'Unprocessed'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed_processing', 'Failed Processing'),
    ]

    name = models.CharField(max_length=255)
    content = models.JSONField() # Parsed CSV content stored as JSON
    schema = models.JSONField(null=True, blank=True)  # Schema extracted from the CSV
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unprocessed',
    )
    failure_reason = models.TextField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"UploadedCSV: {self.name} (Status: {self.get_status_display()})"


class DerivedCSV(models.Model):
    """
    Model to represent a processed version of an uploaded CSV.
    """
    parent = models.ForeignKey(UploadedCSV, on_delete=models.CASCADE, related_name='derived_csvs')
    content = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def name(self):
        """
        Return the name of the parent UploadedCSV as the name of this DerivedCSV.
        """
        return f"Derived of {self.parent.name}"

    def __str__(self):
        return f"DerivedCSV from {self.parent.name} at {self.created_at}"


class CSVChanges(models.Model):
    """
    Model to represent rows added to a CSV (UploadedCSV or DerivedCSV) before processing.
    """
    # Generic relation to either UploadedCSV or DerivedCSV
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    csv_entry = GenericForeignKey('content_type', 'object_id')

    # Data fields
    data = models.JSONField()
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('processed', 'Processed')],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CSVChanges (ID: {self.id}) - Status: {self.get_status_display()}"