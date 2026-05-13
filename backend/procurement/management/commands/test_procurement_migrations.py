from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command
from django.contrib.auth import get_user_model
from procurement.models import (
    ProcurementPlan, QuarterlyTarget, StageHistory, ProcurementStakeholder,
    Timeline, ProcurementRisk, ActivityLog, ProcurementDocument,
    DocumentAccessLog, DocumentApprovalWorkflow, DocumentApprovalStep,
    ApprovalWorkflow, PerformanceMetric, ProcurementNotification,
    ExternalIntegration
)
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Test procurement migrations and create sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run tests without creating actual data',
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Only check if migrations can be applied',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting procurement migration tests...')
        )

        if options['check_only']:
            self.check_migrations_status()
            return

        # Test migration application
        try:
            self.test_migration_application()
            self.test_model_creation()
            
            if not options['dry_run']:
                self.create_sample_data()
                
            self.test_database_constraints()
            self.test_indexes()
            
            self.stdout.write(
                self.style.SUCCESS('All migration tests passed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Migration test failed: {str(e)}')
            )
            raise

    def check_migrations_status(self):
        """Check current migration status"""
        self.stdout.write('Checking migration status...')
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT app, name, applied 
                FROM django_migrations 
                WHERE app = 'procurement' 
                ORDER BY applied DESC
            """)
            migrations = cursor.fetchall()
            
            for app, name, applied in migrations:
                status = "✓" if applied else "✗"
                self.stdout.write(f"{status} {app}.{name} - {applied}")

    def test_migration_application(self):
        """Test that migrations can be applied"""
        self.stdout.write('Testing migration application...')
        
        try:
            # Apply migrations
            call_command('migrate', 'procurement', verbosity=0)
            self.stdout.write(
                self.style.SUCCESS('✓ Migrations applied successfully')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Migration application failed: {str(e)}')
            )
            raise

    def test_model_creation(self):
        """Test that all models can be instantiated"""
        self.stdout.write('Testing model creation...')
        
        # Get or create a test user
        user, created = User.objects.get_or_create(
            employee_id='TEST001',
            defaults={
                'email': 'test@procurement.com',
                'name': 'Test User',
                'username': 'TEST001'
            }
        )
        
        models_to_test = [
            ('ProcurementPlan', ProcurementPlan),
            ('QuarterlyTarget', QuarterlyTarget),
            ('StageHistory', StageHistory),
            ('ProcurementStakeholder', ProcurementStakeholder),
            ('Timeline', Timeline),
            ('ProcurementRisk', ProcurementRisk),
            ('ActivityLog', ActivityLog),
            ('ProcurementDocument', ProcurementDocument),
            ('DocumentAccessLog', DocumentAccessLog),
            ('DocumentApprovalWorkflow', DocumentApprovalWorkflow),
            ('DocumentApprovalStep', DocumentApprovalStep),
            ('ApprovalWorkflow', ApprovalWorkflow),
            ('PerformanceMetric', PerformanceMetric),
            ('ProcurementNotification', ProcurementNotification),
            ('ExternalIntegration', ExternalIntegration),
        ]
        
        for model_name, model_class in models_to_test:
            try:
                # Test model instantiation
                model_class._meta.get_fields()
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {model_name} model structure valid')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ {model_name} model error: {str(e)}')
                )
                raise

    def create_sample_data(self):
        """Create sample data to test model relationships"""
        self.stdout.write('Creating sample data...')
        
        # Get or create test user
        user, created = User.objects.get_or_create(
            employee_id='TEST001',
            defaults={
                'email': 'test@procurement.com',
                'name': 'Test User',
                'username': 'TEST001'
            }
        )
        
        # Create sample ProcurementPlan
        procurement_plan, created = ProcurementPlan.objects.get_or_create(
            policy_number='TEST-2024-001',
            defaults={
                'department': 'Wireline',
                'dept_index': '001',
                'project_name': 'Test Procurement Project',
                'project_description': 'Test procurement for migration validation',
                'estimated_cost': 100000.00,
                'budget': 90000.00,
                'owner': user,
                'stage': 'planning',
                'status': 'draft',
                'priority': 'medium'
            }
        )
        
        if created:
            self.stdout.write('✓ Sample ProcurementPlan created')
        
        # Create related objects to test relationships
        try:
            # QuarterlyTarget
            QuarterlyTarget.objects.get_or_create(
                procurement_plan=procurement_plan,
                quarter='Q1',
                year=2024,
                defaults={
                    'target_description': 'Complete planning phase',
                    'target_value': 25000.00,
                    'status': 'planned'
                }
            )
            
            # ProcurementStakeholder
            ProcurementStakeholder.objects.get_or_create(
                procurement_plan=procurement_plan,
                user=user,
                role='owner',
                defaults={
                    'involvement_level': 'primary',
                    'responsibilities': 'Project oversight and management',
                    'authority_level': 'full_control',
                    'primary_contact': True
                }
            )
            
            # Timeline
            Timeline.objects.get_or_create(
                procurement_plan=procurement_plan,
                stage='planning',
                defaults={
                    'planned_start_date': '2024-01-01',
                    'planned_end_date': '2024-01-31',
                    'is_milestone': True,
                    'milestone_description': 'Planning phase completion',
                    'status': 'active'
                }
            )
            
            # ProcurementRisk
            ProcurementRisk.objects.get_or_create(
                procurement_plan=procurement_plan,
                risk_title='Budget Overrun Risk',
                defaults={
                    'risk_description': 'Risk of exceeding allocated budget',
                    'risk_type': 'financial',
                    'probability': 'medium',
                    'impact': 'moderate',
                    'risk_score': 9.0,
                    'mitigation_strategy': 'Regular budget monitoring and controls',
                    'status': 'identified',
                    'owner': user
                }
            )
            
            # ActivityLog
            ActivityLog.objects.create(
                procurement_plan=procurement_plan,
                action='created',
                action_description='Test procurement plan created',
                user=user,
                user_display_name=user.name,
                severity='info'
            )
            
            # PerformanceMetric
            PerformanceMetric.objects.get_or_create(
                procurement_plan=procurement_plan,
                metric_name='Time to Completion',
                defaults={
                    'metric_type': 'time',
                    'measurement_unit': 'days',
                    'target_value': 90.0,
                    'measurement_period': 'project_lifecycle',
                    'calculation_method': 'Days from start to completion',
                    'responsible_person': user
                }
            )
            
            # ProcurementNotification
            ProcurementNotification.objects.create(
                procurement_plan=procurement_plan,
                recipient=user,
                notification_type='stage_change',
                title='Test Notification',
                message='This is a test notification for migration validation',
                priority='medium',
                status='pending'
            )
            
            # ExternalIntegration
            ExternalIntegration.objects.get_or_create(
                system_name='Test Financial System',
                defaults={
                    'sync_status': 'pending',
                    'api_endpoint': 'https://test-api.example.com',
                    'configuration': {'test': True}
                }
            )
            
            self.stdout.write('✓ Sample related data created')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Sample data creation failed: {str(e)}')
            )
            raise

    def test_database_constraints(self):
        """Test database constraints and relationships"""
        self.stdout.write('Testing database constraints...')
        
        with connection.cursor() as cursor:
            # Test foreign key constraints exist
            cursor.execute("""
                SELECT 
                    tc.constraint_name,
                    tc.table_name,
                    kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = %s
                    AND tc.table_name LIKE 'procurement_%%'
                ORDER BY tc.table_name
            """, [connection.settings_dict['NAME']])
            
            foreign_keys = cursor.fetchall()
            
            if foreign_keys:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Found {len(foreign_keys)} foreign key constraints')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠ No foreign key constraints found')
                )

    def test_indexes(self):
        """Test that performance indexes are created"""
        self.stdout.write('Testing database indexes...')
        
        with connection.cursor() as cursor:
            # Get indexes for procurement tables
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE tablename LIKE 'procurement_%%'
                ORDER BY tablename, indexname
            """)
            
            indexes = cursor.fetchall()
            
            if indexes:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Found {len(indexes)} indexes on procurement tables')
                )
                
                # List some key indexes
                key_indexes = [
                    'procurement_stakeholder_plan_role_idx',
                    'procurement_risk_score_idx',
                    'procurement_activity_timestamp_idx',
                    'procurement_document_type_status_idx'
                ]
                
                index_names = [idx[2] for idx in indexes]
                
                for key_index in key_indexes:
                    if key_index in index_names:
                        self.stdout.write(f'  ✓ {key_index}')
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠ Missing: {key_index}')
                        )
            else:
                self.stdout.write(
                    self.style.WARNING('⚠ No custom indexes found')
                )

    def cleanup_test_data(self):
        """Clean up test data"""
        self.stdout.write('Cleaning up test data...')
        
        try:
            # Delete test procurement plan (cascades to related objects)
            ProcurementPlan.objects.filter(policy_number='TEST-2024-001').delete()
            
            # Delete test user if no other data depends on it
            test_user = User.objects.filter(employee_id='TEST001').first()
            if test_user and not test_user.procurement_plans.exists():
                test_user.delete()
                
            self.stdout.write('✓ Test data cleaned up')
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠ Cleanup warning: {str(e)}')
            )