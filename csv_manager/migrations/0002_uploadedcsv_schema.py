# Generated by Django 5.1.5 on 2025-01-19 11:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('csv_manager', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploadedcsv',
            name='schema',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
