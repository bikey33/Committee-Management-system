from django.db import models
from django.utils import timezone
from users.models import CustomUser


class QuarterlyTarget(models.Model):
    STATUS_CHOICES = (
        ('Planned', 'Planned'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('On Hold', 'On Hold'),
        ('Cancelled', 'Cancelled'),
    )

    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )

    procurement_plan = models.ForeignKey('ProcurementPlan', related_name='quarterly_targets', on_delete=models.CASCADE)
    quarter = models.CharField(max_length=2, choices=[('Q1', 'Q1'), ('Q2', 'Q2'), ('Q3', 'Q3'), ('Q4', 'Q4')])
    target_details = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Planned')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Enhanced tracking fields
    target_start_date = models.DateField(null=True, blank=True, help_text="Planned start date for this quarterly target")
    target_end_date = models.DateField(null=True, blank=True, help_text="Planned completion date for this quarterly target")
    actual_completion_date = models.DateField(null=True, blank=True, help_text="Actual date when target was completed")
    
    # Milestones as JSON field for flexible milestone tracking
    milestones = models.JSONField(
        default=list,
        blank=True,
        help_text="List of milestones with their status and dates"
    )
    
    # Dependencies tracking
    dependencies = models.JSONField(
        default=list,
        blank=True,
        help_text="List of dependencies required before this target can be completed"
    )
    
    # Progress tracking
    progress_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        help_text="Percentage of target completion (0-100)"
    )
    
    # Enhanced notes and documentation
    notes = models.TextField(
        blank=True,
        help_text="Detailed notes, updates, and observations about this quarterly target"
    )
    risk_assessment = models.TextField(
        blank=True,
        help_text="Risk assessment and mitigation strategies"
    )
    
    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_quarterly_targets',
        help_text="User who marked this target as completed"
    )

    class Meta:
        unique_together = ('procurement_plan', 'quarter')
        ordering = ['quarter', 'priority', 'target_end_date']
        verbose_name = "Quarterly Target"
        verbose_name_plural = "Quarterly Targets"
    
    def __str__(self):
        return f"{self.procurement_plan.policy_number} - {self.quarter}: {self.target_details[:50]}"
    
    def is_overdue(self):
        """Check if the quarterly target is overdue"""
        if self.target_end_date and self.status not in ['Completed', 'Cancelled']:
            return timezone.now().date() > self.target_end_date
        return False
    
    def days_until_deadline(self):
        """Calculate days until target end date"""
        if self.target_end_date and self.status not in ['Completed', 'Cancelled']:
            delta = self.target_end_date - timezone.now().date()
            return delta.days
        return None
    
    def get_milestone_summary(self):
        """Get summary of milestone completion"""
        if not self.milestones:
            return {'total': 0, 'completed': 0, 'percentage': 0}
        
        total_milestones = len(self.milestones)
        completed_milestones = sum(1 for m in self.milestones if m.get('status') == 'completed')
        percentage = (completed_milestones / total_milestones * 100) if total_milestones > 0 else 0
        
        return {
            'total': total_milestones,
            'completed': completed_milestones,
            'percentage': round(percentage, 1)
        }
    
    def add_milestone(self, title, description, due_date=None, priority='medium'):
        """Add a new milestone to this quarterly target"""
        milestone = {
            'id': len(self.milestones) + 1,
            'title': title,
            'description': description,
            'due_date': due_date.isoformat() if due_date else None,
            'priority': priority,
            'status': 'planned',
            'created_at': timezone.now().isoformat(),
            'completed_at': None
        }
        
        if not self.milestones:
            self.milestones = []
        self.milestones.append(milestone)
        self.save(update_fields=['milestones'])
        return milestone
    
    def complete_milestone(self, milestone_id, completed_by=None):
        """Mark a milestone as completed"""
        for milestone in self.milestones:
            if milestone.get('id') == milestone_id:
                milestone['status'] = 'completed'
                milestone['completed_at'] = timezone.now().isoformat()
                if completed_by:
                    milestone['completed_by'] = completed_by.username
                break
        
        self.save(update_fields=['milestones'])
        self.update_progress_from_milestones()
    
    def update_progress_from_milestones(self):
        """Update progress percentage based on milestone completion"""
        milestone_summary = self.get_milestone_summary()
        if milestone_summary['total'] > 0:
            self.progress_percentage = milestone_summary['percentage']
            self.save(update_fields=['progress_percentage'])
    
    def check_dependencies(self):
        """Check if all dependencies are satisfied"""
        if not self.dependencies:
            return True
        
        for dep in self.dependencies:
            dep_type = dep.get('type')
            if dep_type == 'quarterly_target':
                # Check if dependent quarterly target is completed
                try:
                    dep_target = QuarterlyTarget.objects.get(id=dep.get('target_id'))
                    if dep_target.status != 'Completed':
                        return False
                except QuarterlyTarget.DoesNotExist:
                    return False
            elif dep_type == 'timeline':
                # Check if procurement plan stage dependency is met
                required_stage = dep.get('stage')
                if self.procurement_plan.stage != required_stage:
                    # Check if we've passed the required stage
                    stage_order = [choice[0] for choice in self.procurement_plan.STAGE_CHOICES]
                    try:
                        current_index = stage_order.index(self.procurement_plan.stage)
                        required_index = stage_order.index(required_stage)
                        if current_index < required_index:
                            return False
                    except ValueError:
                        return False
        
        return True
    
    def add_dependency(self, dep_type, **kwargs):
        """Add a dependency to this quarterly target"""
        dependency = {'type': dep_type, **kwargs}
        
        if not self.dependencies:
            self.dependencies = []
        self.dependencies.append(dependency)
        self.save(update_fields=['dependencies'])
        return dependency
    
    def get_risk_level(self):
        """Calculate risk level based on various factors"""
        risk_score = 0
        
        # Check if overdue
        if self.is_overdue():
            risk_score += 30
        
        # Check progress vs time elapsed
        if self.target_start_date and self.target_end_date:
            current_date = timezone.now().date()
            if current_date >= self.target_start_date:
                total_duration = (self.target_end_date - self.target_start_date).days
                elapsed_duration = (current_date - self.target_start_date).days
                expected_progress = (elapsed_duration / total_duration * 100) if total_duration > 0 else 0
                
                if float(self.progress_percentage) < expected_progress - 20:
                    risk_score += 25
        
        # Check dependencies
        if not self.check_dependencies():
            risk_score += 20
        
        # Priority factor
        if self.priority == 'critical':
            risk_score += 15
        elif self.priority == 'high':
            risk_score += 10
        
        # Determine risk level
        if risk_score >= 50:
            return 'high'
        elif risk_score >= 25:
            return 'medium'
        else:
            return 'low'
    
    def save(self, *args, **kwargs):
        # Auto-update progress if milestones exist
        if self.milestones and not kwargs.get('update_fields') or 'progress_percentage' not in kwargs.get('update_fields', []):
            milestone_progress = self.get_milestone_summary()['percentage']
            if milestone_progress > 0:
                self.progress_percentage = milestone_progress
        
        # Auto-complete if progress is 100%
        if float(self.progress_percentage) >= 100 and self.status != 'Completed':
            self.status = 'Completed'
            if not self.actual_completion_date:
                self.actual_completion_date = timezone.now().date()
        
        super().save(*args, **kwargs)