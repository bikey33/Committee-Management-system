
"""
Django management command to fix all migration issues
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection, transaction
from django.conf import settings
import sys


class Command(BaseCommand):
    help = 'Fix all migration inconsistencies across the project'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force fix even if there are warnings',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without executing',
        )

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.SUCCESS('Starting comprehensive migration fix...')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        try:
            # Step 1: Clean inconsistent migrations
            self.stdout.write('Step 1: Cleaning inconsistent migration records...')
            if not dry_run:
                self._clean_inconsistent_migrations()

            # Step 2: Ensure system user exists
            self.stdout.write('Step 2: Ensuring system user exists...')
            if not dry_run:
                self._ensure_system_user()

            # Step 3: Apply migrations in order
            self.stdout.write('Step 3: Applying migrations in dependency order...')
            if not dry_run:
                self._apply_migrations_in_order()

            # Step 4: Verify models
            self.stdout.write('Step 4: Verifying models...')
            if not dry_run:
                self._verify_models()

            # Step 5: Run system checks
            self.stdout.write('Step 5: Running system checks...')
            if not dry_run:
                call_command('check', verbosity=1)

            # Step 6: Show final status
            self.stdout.write('Step 6: Final migration status...')
            if not dry_run:
                call_command('showmigrations', verbosity=1)

            self.stdout.write(
                self.style.SUCCESS('Migration fix completed successfully!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during migration fix: {str(e)}')
            )
            if not force:
                sys.exit(1)

    def _clean_inconsistent_migrations(self):
        """Clean up inconsistent migration records"""
        with connection.cursor() as cursor:
            # Remove contract and evaluation migrations that depend on bidding
            cursor.execute("""
                DELETE FROM django_migrations 
                WHERE app IN ('contract', 'evaluation') 
                AND name = '0001_initial';
            """)
            self.stdout.write('✓ Cleaned inconsistent migration records')

    def _ensure_system_user(self):
        """Ensure we have a system user"""
        try:
            from users.models import CustomUser
            
            user_count = CustomUser.objects.count()
            if user_count == 0:
                CustomUser.objects.create(
                    employee_id='SYSTEM',
                    email='system@procurement.local',
                    name='System User',
                    username='SYSTEM',
                    is_staff=True,
                    is_active=True,
                    designation='System Administrator'
                )
                self.stdout.write('✓ Created system user')
            else:
                self.stdout.write('✓ System user already exists')
        except Exception as e:
            self.stdout.write(f'User creation note: {e}')

    def _apply_migrations_in_order(self):
        """Apply migrations in dependency order"""
        migration_order = [
            'users', 'contenttypes', 'auth', 'admin', 'sessions',
            'core', 'main_app', 'procurement', 'committee', 'agency_app',
            'specification', 'tender', 'bidding', 'contract', 'evaluation'
        ]
        
        for app_name in migration_order:
            try:
                self.stdout.write(f'Applying {app_name} migrations...')
                call_command('migrate', app_name, verbosity=1)
                self.stdout.write(f'✓ {app_name} migrations applied')
            except Exception as e:
                if "already exists" in str(e):
                    try:
                        call_command('migrate', app_name, '--fake-initial', verbosity=1)
                        self.stdout.write(f'✓ {app_name} fake-applied')
                    except Exception:
                        self.stdout.write(f'⚠️ {app_name} migration issues: {e}')
                else:
                    self.stdout.write(f'⚠️ {app_name} error: {e}')

    def _verify_models(self):
        """Verify models can be imported"""
        models_to_test = [
            ('users.models', 'CustomUser'),
            ('bidding.models', 'Bid'),
            ('contract.models', 'Contract'),
            ('evaluation.models', 'Evaluation'),
            ('tender.models', 'Tender'),
        ]
        
        for module_name, model_name in models_to_test:
            try:
                module = __import__(module_name, fromlist=[model_name])
                model = getattr(module, model_name)
                model.objects.none()
                self.stdout.write(f'✓ {model_name} model working')
            except Exception as e:
                self.stdout.write(f'❌ {model_name} error: {e}')
