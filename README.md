# CSV Manager

CSV Manager is a web application that allows users to upload, process, modify, and visualize CSV files. The system is built with Django for the back-end, Bootstrap for the front-end, and Celery for background tasks. It is designed to handle structured CSV data with features such as real-time data visualization, row-level modifications, and filtered CSV generation.

---

## Features

### 1. **Upload CSV Files**
- Upload structured CSV files to the system.
- Headers are normalized, and a schema is inferred automatically.
- Uploaded files are processed in the background, and derived CSVs are created after filtering.

### 2. **Modify Data**
- Append new rows to existing uploaded or derived CSVs.
- Changes are processed asynchronously to avoid timeouts.
- A new derived CSV is generated upon successful processing of changes.

### 3. **Filter and Process Data**
- Automatically filters integer columns during processing (e.g., dividing values by 2).
- Derived CSVs are stored alongside the original files.

### 4. **Visualize Data**
- Generate dynamic visualizations for univariate and multivariate analysis.
- Choose from bar charts, pie charts, scatter plots, and more.
- Visualization is optimized for the last 400 rows of data.

### 5. **Manage CSV Files**
- View, download, add data, delete, and visualize CSVs from the `My CSVs` page.
- Track all changes in the `My Changes` section, which provides a detailed record of modifications.

---

## Technical Components

### 1. **Back-End**
- **Django**: Handles routing, model interactions, and views.
- **Celery**: Manages background tasks for CSV processing and derived CSV generation.
- **Redis**: Acts as a broker for Celery tasks.

### 2. **Front-End**
- **Bootstrap**: Ensures a modern and responsive design.
- **Chart.js**: Powers the dynamic visualizations.

### 3. **Database**
- **SQLite3**: Stores uploaded files, derived CSVs, and changes.

---

## Setup Instructions

### Prerequisites
- Python 3 or higher
- Docker and Docker Compose
- Redis (for task queuing)

### Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/iem-saad/django_csv_app.git
   cd django_csv_app
2. **Build and Start the Application**
   ```bash
   docker-compose build
   docker-compose up -d
3. **Run Database Migrations**
   ```bash
   docker-compose exec web python manage.py migrate
4. **Access the Application**
   ```bash
   http://localhost:8000
5. **Stopping the Application**
   ```bash
   docker-compose down

## Recommended Input File

While the system is designed to handle generic CSV files with any structure, most of the testing and demonstrations have been done using the **Air Quality Dataset**. It is recommended to use this dataset for testing the functionality of the application.

You can download the dataset from the following link:

[Air Quality Dataset - air-quality-india.csv](https://github.com/iem-saad/django_csv_app/blob/master/air-quality-india.csv)

### Structure of the Dataset

The dataset contains the following columns:

- `Timestamp`: Unique timestamp for each record.
- `Year`: The year of the record.
- `Month`: The month of the record.
- `Day`: The day of the record.
- `Hour`: The hour of the record.
- `PM2.5`: PM2.5 concentration values.

