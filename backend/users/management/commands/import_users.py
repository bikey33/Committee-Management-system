import pandas as pd
from django.core.management.base import BaseCommand
from users.models import EmployeeDetail
import logging
import re

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import Excel data to EmployeeDetail table'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the Excel file')

    def generate_email(self, first_name, last_name, employee_id, existing_emails):
        # Normalize names: remove extra spaces, convert to lowercase
        first_name = re.sub(r'\s+', ' ', first_name.strip()).lower()
        last_name = re.sub(r'\s+', ' ', last_name.strip()).lower()
        # Replace spaces with dots
        first_name = first_name.replace(' ', '.')
        last_name = last_name.replace(' ', '.')

        # Try firstname.lastname@ntc.net.np
        base_email = f"{first_name}.{last_name}@ntc.net.np"
        if base_email not in existing_emails:
            return base_email

        # If duplicate, try firstname.lastnameempid@ntc.net.np
        emp_email = f"{first_name}.{last_name}{employee_id}@ntc.net.np"
        if emp_email not in existing_emails:
            return emp_email

        raise ValueError(f"Cannot generate unique email for {first_name} {last_name} (employee_id: {employee_id})")

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            logger.debug(f"Excel data: {df.to_dict(orient='records')}")

            # Track existing emails to avoid duplicates
            existing_emails = set(EmployeeDetail.objects.values_list('email', flat=True))

            for index, row in df.iterrows():
                try:
                    # Clean and validate employee_id (from eno column)
                    employee_id = str(row['eno']).strip()
                    if not employee_id or employee_id == 'nan':
                        raise ValueError("Empty or invalid employee_id")

                    # Debug specific row
                    if employee_id == '3286':
                        logger.debug(f"Processing row {index}: {row.to_dict()}")

                    # Split Name into first and last names
                    name = str(row['Name']).strip()
                    if not name or name == 'nan':
                        raise ValueError("Empty Name")
                    name_parts = name.split()
                    first_name = name_parts[0] if name_parts else ''
                    last_name = name_parts[-1] if name_parts else 'user'

                    # Generate email
                    email = self.generate_email(first_name, last_name, employee_id, existing_emails)
                    existing_emails.add(email)

                    # Map Excel columns to Employee fields
                    employee_data = {
                        'employee_id': employee_id,
                        'name': name if name else None,
                        'email': email,
                        'position': str(row['Position']).strip() if str(row['Position']).strip() and str(row['Position']) != 'nan' else None,
                        'level': str(row['Level']).strip() if str(row['Level']).strip() and str(row['Level']) != 'nan' else None,
                        'service': str(row['Service']).strip() if str(row['Service']).strip() and str(row['Service']) != 'nan' else None,
                        'group': str(row['Group']).strip() if str(row['Group']).strip() and str(row['Group']) != 'nan' else None,
                        'qualification': str(row['Qualification']).strip() if str(row['Qualification']).strip() and str(row['Qualification']) != 'nan' else None,
                        'seniority': pd.to_datetime(row['Seniority'], errors='coerce') if not pd.isna(row['Seniority']) else None,
                        'retirement': pd.to_datetime(row['Retirement'], errors='coerce') if not pd.isna(row['Retirement']) else None,
                        'mno': str(row['mno']).strip() if str(row['mno']).strip() and str(row['mno']) != 'nan' else None,
                    }

                    # Create or update Employee record
                    employee, created = EmployeeDetail.objects.update_or_create(
                        employee_id=employee_data['employee_id'],
                        defaults=employee_data
                    )

                    if created:
                        self.stdout.write(self.style.SUCCESS(f"Created employee: {employee.employee_id} ({email})"))
                    else:
                        self.stdout.write(self.style.WARNING(f"Updated employee: {employee.employee_id} ({email})"))

                except Exception as e:
                    logger.error(f"Error processing row {index} (eno: {row.get('eno', 'N/A')}): {str(e)}")
                    self.stdout.write(self.style.ERROR(f"Error processing row {index} (eno: {row.get('eno', 'N/A')}): {str(e)}"))

            self.stdout.write(self.style.SUCCESS("Import completed successfully"))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
        except Exception as e:
            logger.error(f"Error importing Excel file: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Error importing Excel file: {str(e)}"))