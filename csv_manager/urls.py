from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('my_csvs/', views.my_csvs, name='my_csvs'),
    path('upload_csv/', views.upload_csv, name='upload_csv'),
    path('download_csv/<int:csv_id>/', views.download_csv, name='download_csv'),
    path('download_csv/<int:csv_id>/derived/', views.download_csv, {'is_derived': True}, name='download_derived_csv'),
    path('delete_csv/<int:csv_id>/', views.delete_csv, name='delete_csv'),
    path('delete_csv/<int:csv_id>/derived/', views.delete_csv, {'is_derived': True}, name='delete_derived_csv'),
    path('view_csv/<int:csv_id>/', views.view_csv, name='view_csv'),
    path('view_csv/<int:csv_id>/derived/', views.view_csv, {'is_derived': True}, name='view_csv_derived'),
    path('add_data_csv/<int:csv_id>/', views.add_data_to_csv, name='add_data_csv'),
    path('visualize_csv/<int:csv_id>/', views.visualize_csv, name='visualize_csv'),
    path('my_changes/', views.my_changes, name='my_changes'),
]