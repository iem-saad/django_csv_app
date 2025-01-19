from django.db import models

class UploadedCSV(models.Model):
    """
    Model to represent the original uploaded CSV file.
    """
    STATUS_CHOICES = [
        ('unprocessed', 'Unprocessed'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
    ]

    name = models.CharField(max_length=255)
    content = models.JSONField() # Parsed CSV content stored as JSON
    schema = models.JSONField(null=True, blank=True)  # Schema extracted from the CSV
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unprocessed',
    )
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

    def __str__(self):
        return f"DerivedCSV from {self.parent.name} at {self.created_at}"