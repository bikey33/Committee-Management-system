"""
Management command to fix migration issues and clean up the database
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.conf import settings
import sys


class Command(BaseCommand):
    help = 'Fix migration issues and clean up the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-migrations',
            action='store_true',
            help='Reset migrations and clean up the database',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without executing',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        reset_migrations = options['reset_migrations']

        self.stdout.write(
            self.style.SUCCESS('Starting migration fix process...')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        try:
            # Step 1: Check current migration status
            self.stdout.write('Checking current migration status...')
            if not dry_run:
                call_command('showmigrations', 'procurement', verbosity=1)

            # Step 2: If reset is requested, clean up migrations
            if reset_migrations:
                self.stdout.write('Resetting migrations...')
                if not dry_run:
                    self._reset_migrations()

            # Step 3: Run makemigrations to create new migration
            self.stdout.write('Creating new migrations...')
            if not dry_run:
                call_command('makemigrations', 'procurement', verbosity=2)

            # Step 4: Apply migrations
            self.stdout.write('Applying migrations...')
            if not dry_run:
                call_command('migrate', 'procurement', verbosity=2)

            # Step 5: Verify the fix
            self.stdout.write('Verifying fix...')
            if not dry_run:
                self._verify_models()

            self.stdout.write(
                self.style.SUCCESS('Migration fix completed successfully!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during migration fix: {str(e)}')
            )
            sys.exit(1)

    def _reset_migrations(self):
        """Reset problematic migrations"""
        with connection.cursor() as cursor:
            # Check if we need to work with PostgreSQL or SQLite
            try:
                # For PostgreSQL
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'procurement_approvalworkflow';
                """)
            except:
                # For SQLite
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM sqlite_master 
                    WHERE type='table' 
                    AND name = 'procurement_approvalworkflow';
                """)
            
            if cursor.fetchone()[0] > 0:
                self.stdout.write('Dropping existing ApprovalWorkflow table...')
                cursor.execute('DROP TABLE IF EXISTS procurement_approvalworkflow CASCADE;')
            
            # Drop dependency table if it exists
            try:
                # For PostgreSQL
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'procurement_approvalworkflowdependency';
                """)
            except:
                # For SQLite
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM sqlite_master 
                    WHERE type='table' 
                    AND name = 'procurement_approvalworkflowdependency';
                """)
            
            if cursor.fetchone()[0] > 0:
                self.stdout.write('Dropping existing ApprovalWorkflowDependency table...')
                cursor.execute('DROP TABLE IF EXISTS procurement_approvalworkflowdependency CASCADE;')

        # Clear migration state for 0010 if it exists
        try:
            # First check if migration 0010 is applied
            call_command('showmigrations', 'procurement', verbosity=0)
            
            # Try to roll back to 0009 if 0010 is applied
            call_command('migrate', 'procurement', '0009', verbosity=1)
            self.stdout.write('Successfully reverted to migration 0009')
        except Exception as e:
            self.stdout.write(f'Note: Could not revert migration (may not be applied): {str(e)}')

    def _verify_models(self):
        """Verify that models can be imported and used"""
        try:
            from procurement.models import ApprovalWorkflow, ApprovalWorkflowDependency
            
            # Try to access the model's meta information
            self.stdout.write(f'ApprovalWorkflow model: {ApprovalWorkflow._meta.db_table}')
            self.stdout.write(f'ApprovalWorkflowDependency model: {ApprovalWorkflowDependency._meta.db_table}')
            
            # Try to create a queryset (without executing)
            ApprovalWorkflow.objects.none()
            ApprovalWorkflowDependency.objects.none()
            
            self.stdout.write(
                self.style.SUCCESS('Model verification passed!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Model verification failed: {str(e)}')
            )
            raise