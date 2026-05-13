
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db import models
from users.models import CustomUser

class Command(BaseCommand):
    help = 'Fix duplicate username issues in CustomUser model'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting username cleanup...'))
        
        with transaction.atomic():
            # Find users with empty usernames
            empty_username_users = CustomUser.objects.filter(username='')
            
            if empty_username_users.exists():
                self.stdout.write(f'Found {empty_username_users.count()} users with empty usernames')
                
                # Delete users with empty usernames (they're likely corrupted)
                deleted_count = empty_username_users.count()
                empty_username_users.delete()
                self.stdout.write(f'Deleted {deleted_count} users with empty usernames')
            
            # Update remaining users to ensure username matches employee_id
            users_to_update = CustomUser.objects.exclude(username=models.F('employee_id'))
            update_count = 0
            
            for user in users_to_update:
                user.username = user.employee_id
                user.save()
                update_count += 1
            
            if update_count > 0:
                self.stdout.write(f'Updated {update_count} users to match username with employee_id')
            
            self.stdout.write(self.style.SUCCESS('Username cleanup completed successfully!'))
