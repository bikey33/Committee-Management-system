import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cms_backend.settings')
django.setup()

from users.models import CustomUser

employee_id = 'admin123'
username = 'admin'
email = 'admin@example.com'
password = 'adminpassword123'

if not CustomUser.objects.filter(employee_id=employee_id).exists():
    CustomUser.objects.create_superuser(employee_id=employee_id, email=email, password=password, username=username)
    print(f"Superuser created successfully with password '{password}'")
else:
    print(f"Superuser already exists.")
