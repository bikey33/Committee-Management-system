from django.db import models
from django.utils import timezone
from users.models import CustomUser
from datetime import timedelta
from .procurement_plan import ProcurementPlan


class Timeline(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
    )

    procurement_plan = models.ForeignKey(ProcurementPlan, related_name='timelines', on_delete=models.CASCADE)
    stage = models.CharField(max_length=20)  # Will be validated against ProcurementPlan.STAGE_CHOICES
    planned_start_date = models.DateField()
    planned_end_date = models.DateField()
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    is_milestone = models.BooleanField(default=False)
    milestone_description = models.CharField(max_length=255, blank=True)
    is_critical_path = models.BooleanField(default=False)
    buffer_days = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    auto_calculated = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('procurement_plan', 'stage')
        ordering = ['planned_start_date']
        verbose_name = "Timeline"
        verbose_name_plural = "Timelines"

    def __str__(self):
        return f"{self.procurement_plan.policy_number} - {self.get_stage_display()}"

    def get_stage_display(self):
        """Get display name for stage"""
        stage_dict = dict(ProcurementPlan.STAGE_CHOICES)
        return stage_dict.get(self.stage, self.stage.title())

    def is_overdue(self):
        """Check if this timeline stage is overdue"""
        if self.status not in ['completed'] and self.planned_end_date:
            return timezone.now().date() > self.planned_end_date
        return False

    def duration_days(self):
        """Calculate planned duration in days"""
        if self.planned_start_date and self.planned_end_date:
            return (self.planned_end_date - self.planned_start_date).days
        return 0

    def actual_duration_days(self):
        """Calculate actual duration in days"""
        if self.actual_start_date and self.actual_end_date:
            return (self.actual_end_date - self.actual_start_date).days
        return None

    def update_status(self):
        """Update status based on current dates and completion"""
        current_date = timezone.now().date()
        
        if self.actual_end_date:
            self.status = 'completed'
        elif self.actual_start_date and current_date <= self.planned_end_date:
            self.status = 'active'
        elif current_date > self.planned_end_date:
            self.status = 'overdue'
        else:
            self.status = 'scheduled'
        
        self.save(update_fields=['status'])

    def save(self, *args, **kwargs):
        # Auto-update status on save
        if not kwargs.get('update_fields') or 'status' not in kwargs.get('update_fields', []):
            current_date = timezone.now().date()
            
            if self.actual_end_date:
                self.status = 'completed'
            elif self.actual_start_date and current_date <= self.planned_end_date:
                self.status = 'active'
            elif current_date > self.planned_end_date and self.status != 'completed':
                self.status = 'overdue'
            else:
                self.status = 'scheduled'
        
        super().save(*args, **kwargs)