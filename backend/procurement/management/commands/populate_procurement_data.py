
import random
import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from faker import Faker

from procurement.models import (
    ProcurementPlan, QuarterlyTarget, Timeline, ProcurementStakeholder,
    ProcurementRisk, ActivityLog, PerformanceMetric, ProcurementDocument,
    DocumentAccessLog, ProcurementNotification, ApprovalWorkflow,
    ApprovalWorkflowDependency
)

User = get_user_model()
fake = Faker()


class Command(BaseCommand):
    help = 'Populate comprehensive procurement plan data with realistic test data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--plans',
            type=int,
            default=75,
            help='Number of procurement plans to create (default: 75)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing procurement data before populating'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting procurement data population...'))
        
        num_plans = options['plans']
        clear_data = options['clear']
        verbose = options['verbose']
        
        if clear_data:
            self.clear_existing_data()
        
        try:
            with transaction.atomic():
                self.create_procurement_data(num_plans, verbose)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Successfully created {num_plans} procurement plans with comprehensive data!')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error during data population: {str(e)}')
            )
            raise

    def clear_existing_data(self):
        """Clear existing procurement data"""
        self.stdout.write('🗑️  Clearing existing procurement data...')
        
        models_to_clear = [
            ProcurementPlan, QuarterlyTarget, Timeline, ProcurementStakeholder,
            ProcurementRisk, ActivityLog, PerformanceMetric, ProcurementDocument,
            DocumentAccessLog, ProcurementNotification, ApprovalWorkflow,
            ApprovalWorkflowDependency
        ]
        
        for model in models_to_clear:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f'   Cleared {count} {model._meta.verbose_name_plural}')

    def create_procurement_data(self, num_plans, verbose):
        """Create comprehensive procurement data"""
        self.stdout.write(f'📋 Creating {num_plans} procurement plans...')
        
        # Get users for realistic assignments
        users = list(User.objects.all())
        
        if not users:
            self.stdout.write(self.style.WARNING('⚠️  No users found. Creating basic test user...'))
            users = [User.objects.create_user(
                email='test@example.com',
                password='testpass123',
                first_name='Test',
                last_name='User'
            )]
        
        # Create procurement plans with associated data
        for i in range(num_plans):
            plan = self.create_procurement_plan(users, i + 1)
            
            if verbose:
                self.stdout.write(f'   Created plan: {plan.policy_number}')
            
            # Create related data
            self.create_quarterly_targets(plan, verbose)
            self.create_timelines(plan, verbose)
            self.create_stakeholders(plan, users, verbose)
            self.create_risks(plan, users, verbose)
            self.create_performance_metrics(plan, users, verbose)
            self.create_documents(plan, users, verbose)
            self.create_activity_logs(plan, users, verbose)
            self.create_approval_workflows(plan, users, verbose)
            self.create_notifications(plan, users, verbose)
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                self.stdout.write(f'   Progress: {i + 1}/{num_plans} plans created')

    def create_procurement_plan(self, users, index):
        """Create a single procurement plan with realistic data"""
        departments = ['Wireline', 'Wireless']
        project_types = [
            'Network Infrastructure Upgrade',
            'Software License Procurement',
            'Hardware Equipment Purchase',
            'Professional Services Contract',
            'Maintenance and Support Agreement',
            'Cloud Services Subscription',
            'Security System Implementation',
            'Telecommunications Equipment',
            'Data Center Expansion',
            'Mobile Device Procurement'
        ]
        
        stages = [choice[0] for choice in ProcurementPlan.STAGE_CHOICES]
        statuses = [choice[0] for choice in ProcurementPlan.STATUS_CHOICES]
        priorities = [choice[0] for choice in ProcurementPlan.PRIORITY_CHOICES]
        
        department = random.choice(departments)
        project_type = random.choice(project_types)
        stage = random.choice(stages)
        status = random.choice(statuses)
        priority = random.choice(priorities)
        
        # Generate realistic costs based on project type
        cost_ranges = {
            'Network Infrastructure Upgrade': (500000, 5000000),
            'Software License Procurement': (50000, 500000),
            'Hardware Equipment Purchase': (100000, 2000000),
            'Professional Services Contract': (75000, 1000000),
            'Maintenance and Support Agreement': (25000, 300000),
            'Cloud Services Subscription': (30000, 400000),
            'Security System Implementation': (200000, 1500000),
            'Telecommunications Equipment': (300000, 3000000),
            'Data Center Expansion': (1000000, 10000000),
            'Mobile Device Procurement': (50000, 500000)
        }
        
        min_cost, max_cost = cost_ranges.get(project_type, (50000, 1000000))
        estimated_cost = random.randint(min_cost, max_cost)
        budget = estimated_cost * random.uniform(0.85, 0.95)
        
        # Generate realistic dates
        start_date = fake.date_between(start_date='-1y', end_date='+3m')
        end_date = start_date + timedelta(days=random.randint(90, 365))
        
        # Create policy number
        policy_number = f"{department.upper()}-{datetime.now().year}-{index:04d}"
        
        plan = ProcurementPlan.objects.create(
            policy_number=policy_number,
            department=department,
            project_name=f"{project_type} - {fake.company()} ({index})",
            project_description=self.generate_project_description(project_type),
            estimated_cost=estimated_cost,
            budget=budget,
            stage=stage,
            status=status,
            priority=priority,
            progress_percentage=self.calculate_progress_for_stage(stage),
            planned_start_date=start_date,
            planned_end_date=end_date,
            owner=random.choice(users),
            created_at=fake.date_time_between(start_date='-6m', end_date='now', tzinfo=timezone.get_current_timezone()),
            stage_updated_at=fake.date_time_between(start_date='-3m', end_date='now', tzinfo=timezone.get_current_timezone())
        )
        
        return plan

    def generate_project_description(self, project_type):
        """Generate realistic project description based on type"""
        descriptions = {
            'Network Infrastructure Upgrade': [
                "Comprehensive upgrade of network infrastructure including switches, routers, and fiber optic cables to support increased bandwidth requirements and improve network reliability.",
                "Modernization of legacy network equipment to support next-generation services and improve operational efficiency.",
                "Implementation of redundant network paths and failover systems to ensure 99.9% uptime for critical business operations."
            ],
            'Software License Procurement': [
                "Procurement of enterprise software licenses for productivity tools, security software, and specialized applications.",
                "Renewal and expansion of existing software licenses to support business growth and new user requirements.",
                "Acquisition of cloud-based software solutions to improve collaboration and reduce IT infrastructure costs."
            ],
            'Hardware Equipment Purchase': [
                "Purchase of servers, workstations, and networking equipment to support business operations and growth.",
                "Procurement of specialized hardware for data processing, storage, and backup systems.",
                "Acquisition of mobile devices and accessories for field operations and remote work capabilities."
            ],
            'Professional Services Contract': [
                "Engagement of external consultants for system integration, project management, and technical expertise.",
                "Procurement of professional services for audit, compliance, and risk management activities.",
                "Contract for specialized training and knowledge transfer services for technical staff."
            ],
            'Maintenance and Support Agreement': [
                "Comprehensive maintenance and support agreement for critical IT infrastructure and equipment.",
                "Extended warranty and support services for network equipment and software systems.",
                "Preventive maintenance and emergency response services for telecommunications infrastructure."
            ]
        }
        
        options = descriptions.get(project_type, [
            "Procurement of goods and services to support business operations and strategic objectives.",
            "Implementation of new systems and processes to improve efficiency and reduce costs.",
            "Upgrade of existing infrastructure to meet current standards and future requirements."
        ])
        
        return random.choice(options)

    def calculate_progress_for_stage(self, stage):
        """Calculate realistic progress percentage based on stage"""
        stage_progress = {
            'planning': random.uniform(5, 15),
            'specification': random.uniform(20, 30),
            'tender': random.uniform(30, 40),
            'committee': random.uniform(40, 50),
            'bidding': random.uniform(55, 65),
            'evaluation': random.uniform(70, 80),
            'contract': random.uniform(80, 90),
            'complaint': random.uniform(90, 95),
            'management': random.uniform(95, 100)
        }
        return round(stage_progress.get(stage, 0), 2)

    def create_quarterly_targets(self, plan, verbose):
        """Create quarterly targets for the procurement plan"""
        quarters = ['Q1', 'Q2', 'Q3', 'Q4']
        num_targets = random.randint(2, 4)
        
        for i in range(num_targets):
            quarter = random.choice(quarters)
            
            # Ensure unique quarter per plan
            if QuarterlyTarget.objects.filter(procurement_plan=plan, quarter=quarter).exists():
                continue
            
            target = QuarterlyTarget.objects.create(
                procurement_plan=plan,
                quarter=quarter,
                target_details=self.generate_target_details(quarter, plan.stage),
                status=random.choice([choice[0] for choice in QuarterlyTarget.STATUS_CHOICES]),
                priority=random.choice([choice[0] for choice in QuarterlyTarget.PRIORITY_CHOICES]),
                target_start_date=fake.date_between(start_date='-3m', end_date='+6m'),
                target_end_date=fake.date_between(start_date='+1m', end_date='+9m'),
                progress_percentage=random.uniform(0, 100),
                notes=fake.text(max_nb_chars=200),
                milestones=self.generate_milestones(),
                dependencies=self.generate_dependencies(),
                risk_assessment=fake.text(max_nb_chars=150)
            )
            
            if verbose:
                self.stdout.write(f'     Created quarterly target: {target.quarter}')

    def generate_target_details(self, quarter, stage):
        """Generate realistic target details based on quarter and stage"""
        details = {
            'Q1': [
                "Complete initial planning and requirements gathering phase",
                "Finalize technical specifications and vendor pre-qualification",
                "Obtain necessary approvals and budget allocation"
            ],
            'Q2': [
                "Publish tender documents and conduct market consultation",
                "Evaluate proposals and conduct technical assessments",
                "Complete vendor selection and negotiation process"
            ],
            'Q3': [
                "Finalize contract terms and execute agreements",
                "Begin implementation and project kickoff activities",
                "Establish project governance and monitoring systems"
            ],
            'Q4': [
                "Complete project delivery and acceptance testing",
                "Conduct final reviews and documentation",
                "Transition to operational support and maintenance"
            ]
        }
        
        return random.choice(details.get(quarter, ["Complete quarterly objectives and deliverables"]))

    def generate_milestones(self):
        """Generate realistic milestones for quarterly targets"""
        milestone_types = [
            "Requirements Analysis Complete",
            "Technical Specification Approved",
            "Vendor Pre-qualification Finished",
            "Tender Publication",
            "Proposal Evaluation Complete",
            "Contract Negotiation Finished",
            "Project Implementation Started",
            "Acceptance Testing Complete",
            "Go-Live Achieved"
        ]
        
        num_milestones = random.randint(2, 5)
        milestones = []
        
        for i in range(num_milestones):
            milestone = {
                'id': i + 1,
                'title': random.choice(milestone_types),
                'description': fake.text(max_nb_chars=100),
                'due_date': fake.date_between(start_date='-1m', end_date='+3m').isoformat(),
                'priority': random.choice(['low', 'medium', 'high']),
                'status': random.choice(['planned', 'active', 'completed']),
                'created_at': fake.date_time_between(start_date='-1m', end_date='now').isoformat(),
                'completed_at': fake.date_time_between(start_date='-1m', end_date='now').isoformat() if random.choice([True, False]) else None
            }
            milestones.append(milestone)
        
        return milestones

    def generate_dependencies(self):
        """Generate realistic dependencies for quarterly targets"""
        dependencies = []
        
        if random.choice([True, False]):
            dependency = {
                'type': 'timeline',
                'stage': random.choice(['planning', 'specification', 'tender']),
                'description': 'Dependent on completion of previous procurement stage'
            }
            dependencies.append(dependency)
        
        return dependencies

    def create_timelines(self, plan, verbose):
        """Create timeline entries for the procurement plan"""
        plan.generate_stage_timelines()
        
        if verbose:
            self.stdout.write(f'     Created {plan.timelines.count()} timeline entries')

    def create_stakeholders(self, plan, users, verbose):
        """Create stakeholders for the procurement plan"""
        roles = [
            'Project Manager',
            'Technical Lead',
            'Procurement Officer',
            'Financial Analyst',
            'Legal Advisor',
            'Quality Assurance',
            'Operations Manager',
            'Vendor Manager'
        ]
        
        num_stakeholders = random.randint(3, 8)
        
        for i in range(num_stakeholders):
            stakeholder = ProcurementStakeholder.objects.create(
                procurement_plan=plan,
                user=random.choice(users),
                role=random.choice(roles),
                responsibilities=fake.text(max_nb_chars=200),
                authority_level=random.choice([choice[0] for choice in ProcurementStakeholder.AUTHORITY_LEVELS]),
                notification_preferences=random.choice([choice[0] for choice in ProcurementStakeholder.NOTIFICATION_PREFERENCES]),
                is_primary=i == 0,
                is_active=random.choice([True, True, True, False])  # 75% active
            )
            
            if verbose:
                self.stdout.write(f'     Created stakeholder: {stakeholder.role}')

    def create_risks(self, plan, users, verbose):
        """Create risks for the procurement plan"""
        risk_scenarios = [
            {
                'title': 'Vendor Delivery Delays',
                'description': 'Risk of delays in vendor delivery due to supply chain issues or capacity constraints',
                'type': 'vendor',
                'probability': 'medium',
                'impact': 'moderate'
            },
            {
                'title': 'Budget Overrun',
                'description': 'Risk of exceeding allocated budget due to scope changes or market price fluctuations',
                'type': 'financial',
                'probability': 'low',
                'impact': 'major'
            },
            {
                'title': 'Technical Specification Changes',
                'description': 'Risk of requiring specification changes during implementation phase',
                'type': 'technical',
                'probability': 'medium',
                'impact': 'moderate'
            },
            {
                'title': 'Regulatory Compliance Issues',
                'description': 'Risk of non-compliance with regulatory requirements affecting project approval',
                'type': 'regulatory',
                'probability': 'low',
                'impact': 'critical'
            },
            {
                'title': 'Key Personnel Unavailability',
                'description': 'Risk of key project personnel being unavailable during critical phases',
                'type': 'operational',
                'probability': 'medium',
                'impact': 'minor'
            }
        ]
        
        num_risks = random.randint(2, 6)
        
        for i in range(num_risks):
            risk_data = random.choice(risk_scenarios)
            
            risk = ProcurementRisk.objects.create(
                procurement_plan=plan,
                risk_title=risk_data['title'],
                risk_description=risk_data['description'],
                risk_type=risk_data['type'],
                probability=risk_data['probability'],
                impact=risk_data['impact'],
                mitigation_strategy=fake.text(max_nb_chars=300),
                mitigation_actions=self.generate_mitigation_actions(),
                status=random.choice([choice[0] for choice in ProcurementRisk.STATUS_CHOICES]),
                owner=random.choice(users),
                target_resolution_date=fake.date_between(start_date='+1m', end_date='+6m'),
                cost_impact=random.randint(1000, 50000) if random.choice([True, False]) else None,
                schedule_impact_days=random.randint(1, 30) if random.choice([True, False]) else None
            )
            
            if verbose:
                self.stdout.write(f'     Created risk: {risk.risk_title}')

    def generate_mitigation_actions(self):
        """Generate realistic mitigation actions"""
        actions = [
            {
                'action': 'Establish backup vendor relationships',
                'responsible': 'Procurement Officer',
                'due_date': fake.date_between(start_date='+1w', end_date='+1m').isoformat(),
                'status': 'planned'
            },
            {
                'action': 'Conduct regular progress reviews',
                'responsible': 'Project Manager',
                'due_date': fake.date_between(start_date='+2w', end_date='+2m').isoformat(),
                'status': 'active'
            },
            {
                'action': 'Implement contingency budget allocation',
                'responsible': 'Financial Analyst',
                'due_date': fake.date_between(start_date='+1w', end_date='+6w').isoformat(),
                'status': 'completed'
            }
        ]
        
        return random.sample(actions, random.randint(1, 3))

    def create_performance_metrics(self, plan, users, verbose):
        """Create performance metrics for the procurement plan"""
        metric_types = [
            {
                'type': 'cost',
                'name': 'Cost Variance',
                'unit': 'percentage',
                'target': 5.0,
                'description': 'Variance between actual and planned costs'
            },
            {
                'type': 'schedule',
                'name': 'Schedule Adherence',
                'unit': 'percentage',
                'target': 95.0,
                'description': 'Percentage of milestones completed on time'
            },
            {
                'type': 'quality',
                'name': 'Quality Score',
                'unit': 'score',
                'target': 85.0,
                'description': 'Overall quality assessment score'
            },
            {
                'type': 'vendor',
                'name': 'Vendor Performance',
                'unit': 'rating',
                'target': 4.0,
                'description': 'Vendor performance rating (1-5 scale)'
            }
        ]
        
        num_metrics = random.randint(2, 4)
        
        for i in range(num_metrics):
            metric_data = random.choice(metric_types)
            
            current_value = metric_data['target'] * random.uniform(0.8, 1.2)
            
            metric = PerformanceMetric.objects.create(
                procurement_plan=plan,
                metric_type=metric_data['type'],
                metric_name=metric_data['name'],
                description=metric_data['description'],
                unit=metric_data['unit'],
                current_value=current_value,
                target_value=metric_data['target'],
                baseline_value=metric_data['target'] * random.uniform(0.7, 0.9),
                status=self.calculate_metric_status(current_value, metric_data['target']),
                measurement_date=fake.date_between(start_date='-1m', end_date='now'),
                frequency=random.choice([choice[0] for choice in PerformanceMetric.FREQUENCY_CHOICES]),
                auto_calculated=random.choice([True, False]),
                owner=random.choice(users),
                measured_by=random.choice(users),
                notes=fake.text(max_nb_chars=150)
            )
            
            if verbose:
                self.stdout.write(f'     Created metric: {metric.metric_name}')

    def calculate_metric_status(self, current, target):
        """Calculate metric status based on current vs target values"""
        variance = abs(current - target) / target * 100
        
        if variance <= 5:
            return 'on_target'
        elif variance <= 15:
            return 'above_target' if current > target else 'below_target'
        else:
            return 'at_risk'

    def create_documents(self, plan, users, verbose):
        """Create documents for the procurement plan"""
        document_types = [
            {
                'name': 'Technical Specifications',
                'type': 'specification',
                'stage': 'specification'
            },
            {
                'name': 'Tender Documents',
                'type': 'tender',
                'stage': 'tender'
            },
            {
                'name': 'Vendor Proposals',
                'type': 'proposal',
                'stage': 'bidding'
            },
            {
                'name': 'Evaluation Report',
                'type': 'evaluation',
                'stage': 'evaluation'
            },
            {
                'name': 'Contract Agreement',
                'type': 'contract',
                'stage': 'contract'
            }
        ]
        
        num_documents = random.randint(2, 5)
        
        for i in range(num_documents):
            doc_data = random.choice(document_types)
            
            document = ProcurementDocument.objects.create(
                procurement_plan=plan,
                document_name=doc_data['name'],
                document_type=doc_data['type'],
                file_path=f"/documents/{plan.policy_number}/{doc_data['name'].lower().replace(' ', '_')}.pdf",
                file_size=random.randint(1024, 10485760),  # 1KB to 10MB
                uploaded_by=random.choice(users),
                stage=doc_data['stage'],
                version=f"v{random.randint(1, 5)}.{random.randint(0, 9)}",
                is_active=True,
                requires_approval=random.choice([True, False]),
                approval_status=random.choice([choice[0] for choice in ProcurementDocument.APPROVAL_STATUS_CHOICES]) if random.choice([True, False]) else 'pending',
                description=fake.text(max_nb_chars=200)
            )
            
            if verbose:
                self.stdout.write(f'     Created document: {document.document_name}')

    def create_activity_logs(self, plan, users, verbose):
        """Create activity logs for the procurement plan"""
        activities = [
            'Plan created',
            'Stage advanced',
            'Document uploaded',
            'Stakeholder added',
            'Risk identified',
            'Milestone completed',
            'Budget updated',
            'Timeline adjusted',
            'Approval requested',
            'Contract signed'
        ]
        
        num_activities = random.randint(5, 15)
        
        for i in range(num_activities):
            activity = ActivityLog.objects.create(
                procurement_plan=plan,
                activity_type=random.choice(['create', 'update', 'delete', 'approve', 'reject']),
                activity_description=random.choice(activities),
                user=random.choice(users),
                timestamp=fake.date_time_between(start_date='-3m', end_date='now', tzinfo=timezone.get_current_timezone()),
                ip_address=fake.ipv4(),
                user_agent=fake.user_agent(),
                additional_data={'action': random.choice(activities)}
            )
            
            if verbose and i < 3:  # Only log first few to avoid spam
                self.stdout.write(f'     Created activity: {activity.activity_description}')

    def create_approval_workflows(self, plan, users, verbose):
        """Create approval workflows for the procurement plan"""
        workflow_types = [
            'Budget Approval',
            'Technical Approval',
            'Contract Approval',
            'Vendor Selection Approval'
        ]
        
        if random.choice([True, False]):  # 50% chance of having approval workflow
            workflow = ApprovalWorkflow.objects.create(
                procurement_plan=plan,
                workflow_name=random.choice(workflow_types),
                workflow_type=random.choice(['sequential', 'parallel']),
                required_approvals=random.randint(2, 4),
                current_step=random.randint(1, 3),
                status=random.choice([choice[0] for choice in ApprovalWorkflow.STATUS_CHOICES]),
                created_by=random.choice(users),
                workflow_config={'steps': ['Step 1', 'Step 2', 'Step 3']},
                auto_advance=random.choice([True, False])
            )
            
            if verbose:
                self.stdout.write(f'     Created approval workflow: {workflow.workflow_name}')

    def create_notifications(self, plan, users, verbose):
        """Create notifications for the procurement plan"""
        notification_types = [
            'Stage advancement',
            'Deadline reminder',
            'Budget alert',
            'Risk notification',
            'Approval request',
            'Document uploaded'
        ]
        
        num_notifications = random.randint(2, 8)
        
        for i in range(num_notifications):
            notification = ProcurementNotification.objects.create(
                procurement_plan=plan,
                recipient=random.choice(users),
                notification_type=random.choice(['email', 'sms', 'push', 'in_app']),
                title=f"{random.choice(notification_types)} - {plan.policy_number}",
                message=fake.text(max_nb_chars=200),
                is_read=random.choice([True, False]),
                priority=random.choice(['low', 'medium', 'high']),
                scheduled_for=fake.date_time_between(start_date='-1m', end_date='+1m', tzinfo=timezone.get_current_timezone()),
                sent_at=fake.date_time_between(start_date='-1m', end_date='now', tzinfo=timezone.get_current_timezone()) if random.choice([True, False]) else None
            )
            
            if verbose and i < 2:  # Only log first few
                self.stdout.write(f'     Created notification: {notification.title}')
