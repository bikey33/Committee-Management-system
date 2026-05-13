from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from users.models import CustomUser
from datetime import datetime, timedelta


class ProcurementPlan(models.Model):
    # Define the stages of the procurement flow
    STAGE_CHOICES = (
        ('planning', 'Procurement Planning'),
        ('specification', 'Specification Preparation'),
        ('spec_review', 'Specification Review'),
        ('tender', 'Tender Creation & Publication'),
        ('committee', 'Committee Formation'),
        ('bidding', 'Bidding Process'),
        ('evaluation', 'Bid Evaluation'),
        ('loa', 'Letter of Acceptance'),
        ('loi', 'Letter of Intent'),
        ('loa_loi', 'Letter of Acceptance/Intent (Legacy)'),
        ('contract_prep', 'Contract Preparation'),
        ('final_contract', 'Final Contract'),
        ('contract', 'Contract Award'),
        ('complaint', 'Complaint Handling'),
        ('management', 'Contract Management & Payment'),
    )

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )

    # Basic Information
    policy_number = models.CharField(max_length=50)
    department = models.CharField(max_length=100)  # Matches Department.name
    office = models.ForeignKey('users.Office', on_delete=models.SET_NULL, null=True, blank=True, related_name='procurement_plans', help_text="The office this procurement plan belongs to")
    dept_index = models.CharField(max_length=10)
    fiscal_year = models.CharField(max_length=10, default='2080/81')
    program_number = models.CharField(max_length=50, blank=True)
    project_name = models.CharField(max_length=200)
    project_description = models.TextField()

    # Financial Information
    estimated_cost = models.DecimalField(max_digits=20, decimal_places=2)
    budget = models.DecimalField(max_digits=20, decimal_places=2)

    # Status and Progress Tracking
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='planning')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    progress_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    # Deadline Management
    planned_start_date = models.DateField(null=True, blank=True)
    planned_end_date = models.DateField(null=True, blank=True)
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    next_milestone_date = models.DateField(null=True, blank=True)
    next_milestone_description = models.CharField(max_length=255, blank=True)

    # Relationships
    owner = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    committee = models.ForeignKey('committee.Committee', null=True, blank=True, on_delete=models.SET_NULL)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    stage_updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Procurement Plan"
        verbose_name_plural = "Procurement Plans"

    def __str__(self):
        return f"{self.policy_number} - {self.project_name}"

    def proposed_budget_percentage(self):
        """Calculate the proposed budget as a percentage of estimated cost"""
        if self.estimated_cost is None or self.estimated_cost == 0:
            return 0.0
        return round((float(self.budget) / float(self.estimated_cost)) * 100, 2)

    # Rest of the model methods (get_stage_display_info, calculate_progress_percentage, etc.) remain unchanged
    def get_stage_display_info(self):
        """Get detailed information about the current stage"""
        stage_info = {
            'planning': {
                'description': 'Initial planning and requirements gathering',
                'next_stage': 'specification',
                'typical_duration_days': 14
            },
            'specification': {
                'description': 'Technical specification preparation and review',
                'next_stage': 'spec_review',
                'typical_duration_days': 21
            },
            'spec_review': {
                'description': 'Review and approve specification documents',
                'next_stage': 'tender',
                'typical_duration_days': 10
            },
            'tender': {
                'description': 'Tender document creation and publication',
                'next_stage': 'committee',
                'typical_duration_days': 7
            },
            'committee': {
                'description': 'Evaluation committee formation',
                'next_stage': 'bidding',
                'typical_duration_days': 5
            },
            'bidding': {
                'description': 'Bidding process and submission collection',
                'next_stage': 'evaluation',
                'typical_duration_days': 30
            },
            'evaluation': {
                'description': 'Bid evaluation and analysis',
                'next_stage': 'loi',
                'typical_duration_days': 21
            },
            'loi': {
                'description': 'Issue LOI to the winning bidder',
                'next_stage': 'loa',
                'typical_duration_days': 7
            },
            'loa': {
                'description': 'Issue LOA to the winning bidder',
                'next_stage': 'contract_prep',
                'typical_duration_days': 7
            },
            'loa_loi': {
                'description': 'Issue LOA/LOI to the winning bidder',
                'next_stage': 'contract_prep',
                'typical_duration_days': 7
            },
            'contract_prep': {
                'description': 'Draft and finalize contract',
                'next_stage': 'final_contract',
                'typical_duration_days': 14
            },
            'final_contract': {
                'description': 'Sign contract and complete handover',
                'next_stage': None,
                'typical_duration_days': 14
            },
            'contract': {
                'description': 'Contract award and finalization',
                'next_stage': 'complaint',
                'typical_duration_days': 14
            },
            'complaint': {
                'description': 'Complaint period and resolution',
                'next_stage': 'management',
                'typical_duration_days': 14
            },
            'management': {
                'description': 'Contract management and execution',
                'next_stage': None,
                'typical_duration_days': 365
            }
        }
        return stage_info.get(self.stage, {})

    def calculate_progress_percentage(self):
        """Calculate progress based on current stage and completion status"""
        stage_progress = {
            'planning': 10,
            'specification': 25,
            'spec_review': 35,
            'tender': 35,
            'committee': 45,
            'bidding': 60,
            'evaluation': 75,
            'loi': 80,
            'loa': 85,
            'loa_loi': 80,
            'contract_prep': 90,
            'final_contract': 100,
            'contract': 85,
            'complaint': 95,
            'management': 100
        }
        return stage_progress.get(self.stage, 0)

    def update_progress(self):
        """Update progress percentage based on current stage"""
        self.progress_percentage = self.calculate_progress_percentage()
        self.save(update_fields=['progress_percentage'])

    def advance_stage(self, user, notes=''):
        """Move to the next stage with history tracking"""
        from .stage_history import StageHistory

        stage_info = self.get_stage_display_info()
        next_stage = stage_info.get('next_stage')

        if not next_stage:
            raise ValidationError("Cannot advance from the final stage")

        # Validate stage transition
        if not self.can_advance_to_stage(next_stage):
            raise ValidationError(f"Cannot advance to {next_stage} stage. Prerequisites not met.")

        # Record stage history
        StageHistory.objects.create(
            procurement_plan=self,
            previous_stage=self.stage,
            new_stage=next_stage,
            changed_by=user,
            notes=notes
        )

        # Update stage and related fields
        old_stage = self.stage
        self.stage = next_stage
        self.stage_updated_at = timezone.now()
        self.update_progress()

        # Auto-update status based on stage
        if next_stage == 'management':
            self.status = 'completed'
        elif old_stage == 'planning' and next_stage == 'specification':
            self.status = 'active'

        self.save()

    def can_advance_to_stage(self, target_stage):
        """Check if advancement to target stage is allowed"""
        # Define stage prerequisites
        prerequisites = {
            'specification': lambda: True,  # Can always move from planning
            'tender': lambda: hasattr(self, 'specification') and self.specification is not None,
            'committee': lambda: hasattr(self, 'tender') and self.tender is not None,
            'bidding': lambda: self.committee is not None,
            'evaluation': lambda: hasattr(self, 'tender') and self.tender.status == 'closed',
            'contract': lambda: True,  # Evaluation complete
            'complaint': lambda: True,  # Contract awarded
            'management': lambda: True,  # Complaint period over
        }

        prerequisite_check = prerequisites.get(target_stage, lambda: False)
        return prerequisite_check()

    def is_overdue(self):
        """Check if the project is overdue based on planned end date"""
        if self.planned_end_date and self.status not in ['completed', 'cancelled']:
            return timezone.now().date() > self.planned_end_date
        return False

    def days_until_deadline(self):
        """Calculate days until planned end date"""
        if self.planned_end_date and self.status not in ['completed', 'cancelled']:
            delta = self.planned_end_date - timezone.now().date()
            return delta.days
        return None

    def get_status_color(self):
        """Get color code for status display"""
        colors = {
            'draft': 'gray',
            'active': 'blue',
            'on_hold': 'yellow',
            'completed': 'green',
            'cancelled': 'red',
        }
        return colors.get(self.status, 'gray')

    def get_priority_color(self):
        """Get color code for priority display"""
        colors = {
            'low': 'green',
            'medium': 'yellow',
            'high': 'orange',
            'urgent': 'red',
        }
        return colors.get(self.priority, 'gray')

    def generate_stage_timelines(self):
        """Generate timeline entries for all stages based on planned dates"""
        from .timeline import Timeline

        if not self.planned_start_date or not self.planned_end_date:
            return False

        # Delete existing auto-calculated timelines
        self.timelines.filter(auto_calculated=True).delete()

        # Get stage duration mapping
        stage_durations = {}
        for stage_key, _ in self.STAGE_CHOICES:
            stage_info = self.get_stage_display_info()
            if stage_key == self.stage:
                stage_durations[stage_key] = stage_info.get('typical_duration_days', 14)
            else:
                # Get stage info for each stage
                temp_stage = self.stage
                self.stage = stage_key
                stage_info = self.get_stage_display_info()
                stage_durations[stage_key] = stage_info.get('typical_duration_days', 14)
                self.stage = temp_stage

        # Calculate timeline for each stage
        current_start = self.planned_start_date
        total_project_days = (self.planned_end_date - self.planned_start_date).days

        for stage_key, stage_name in self.STAGE_CHOICES:
            duration = stage_durations[stage_key]

            # Adjust for overall project timeline
            if stage_key == 'management':
                # Management stage takes remaining time
                stage_end = self.planned_end_date
            else:
                stage_end = current_start + timedelta(days=duration)

            # Determine if this is a milestone stage
            milestone_stages = ['specification', 'tender', 'committee', 'evaluation', 'contract']
            is_milestone = stage_key in milestone_stages

            # Determine critical path (stages that can't be delayed)
            critical_stages = ['tender', 'bidding', 'evaluation', 'contract']
            is_critical = stage_key in critical_stages

            Timeline.objects.create(
                procurement_plan=self,
                stage=stage_key,
                planned_start_date=current_start,
                planned_end_date=stage_end,
                is_milestone=is_milestone,
                milestone_description=f"{stage_name} completion",
                is_critical_path=is_critical,
                buffer_days=0 if is_critical else 2,
                auto_calculated=True
            )

            current_start = stage_end

        return True

    def update_timeline_on_stage_change(self):
        """Update timeline actual dates when stage advances"""
        current_date = timezone.now().date()

        # Get current stage timeline
        try:
            current_timeline = self.timelines.get(stage=self.stage)
            if not current_timeline.actual_start_date:
                current_timeline.actual_start_date = current_date
                current_timeline.save()
        except:
            # Create timeline if it doesn't exist
            self.generate_stage_timelines()

        # Mark previous stages as completed if not already
        stage_order = [choice[0] for choice in self.STAGE_CHOICES]
        try:
            current_index = stage_order.index(self.stage)
            for i in range(current_index):
                prev_stage = stage_order[i]
                try:
                    prev_timeline = self.timelines.get(stage=prev_stage)
                    if not prev_timeline.actual_end_date:
                        prev_timeline.actual_end_date = current_date
                        prev_timeline.save()
                except:
                    continue
        except ValueError:
            pass

    def get_upcoming_milestones(self, days_ahead=30):
        """Get milestones coming up within specified days"""
        current_date = timezone.now().date()
        future_date = current_date + timedelta(days=days_ahead)

        return self.timelines.filter(
            is_milestone=True,
            planned_end_date__gte=current_date,
            planned_end_date__lte=future_date,
            status__in=['scheduled', 'active']
        ).order_by('planned_end_date')

    def calculate_critical_path(self):
        """Calculate and update critical path for the project"""
        critical_timelines = self.timelines.filter(is_critical_path=True).order_by('planned_start_date')

        # Update critical path based on dependencies and delays
        for timeline in critical_timelines:
            if timeline.is_overdue() and timeline.status != 'completed':
                # Mark subsequent timelines as potentially delayed
                later_timelines = self.timelines.filter(
                    planned_start_date__gt=timeline.planned_end_date
                )
                for later_timeline in later_timelines:
                    if later_timeline.auto_calculated:
                        delay_days = (timezone.now().date() - timeline.planned_end_date).days
                        later_timeline.planned_start_date += timedelta(days=delay_days)
                        later_timeline.planned_end_date += timedelta(days=delay_days)
                        later_timeline.save()

    def adjust_timeline(self, stage, new_end_date, reason="Manual adjustment"):
        """Adjust timeline for a specific stage and propagate changes"""
        try:
            timeline = self.timelines.get(stage=stage)
            old_end_date = timeline.planned_end_date
            timeline.planned_end_date = new_end_date
            timeline.auto_calculated = False
            timeline.save()

            # Propagate changes to subsequent stages
            if new_end_date > old_end_date:
                delay_days = (new_end_date - old_end_date).days
                subsequent_timelines = self.timelines.filter(
                    planned_start_date__gt=old_end_date,
                    auto_calculated=True
                ).order_by('planned_start_date')

                for sub_timeline in subsequent_timelines:
                    sub_timeline.planned_start_date += timedelta(days=delay_days)
                    sub_timeline.planned_end_date += timedelta(days=delay_days)
                    sub_timeline.save()

            return True
        except:
            return False

    def save(self, *args, **kwargs):
        # Extract dept_index from policy_number
        if self.policy_number:
            dept_index = self.policy_number.split('-')[-1]
            self.dept_index = dept_index[:10]

        # Auto-update progress if stage changed
        if self.pk:
            try:
                old_instance = ProcurementPlan.objects.get(pk=self.pk)
                if old_instance.stage != self.stage:
                    self.progress_percentage = self.calculate_progress_percentage()
                    self.stage_updated_at = timezone.now()
            except ProcurementPlan.DoesNotExist:
                pass

        super().save(*args, **kwargs)
