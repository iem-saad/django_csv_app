from django.core.mail import EmailMessage

def send_csv_email(to_email, subject, message, csv_content, filename='filtered_csv.csv'):
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email='your_email@example.com',
        to=[to_email]
    )

    email.attach(filename, csv_content, 'text/csv')
    email.send()