from django.db import models
from django.utils import timezone
from users.models import CustomUser
from decimal import Decimal


class PerformanceMetric(models.Model):
    METRIC_TYPES = [
        ('cost_variance', 'Cost Variance'),
        ('schedule_variance', 'Schedule Variance'),
        ('budget_utilization', 'Budget Utilization'),
        ('timeline_adherence', 'Timeline Adherence'),
        ('approval_time', 'Average Approval Time'),
        ('vendor_response_time', 'Vendor Response Time'),
        ('document_processing_time', 'Document Processing Time'),
        ('stakeholder_satisfaction', 'Stakeholder Satisfaction'),
        ('risk_mitigation_rate', 'Risk Mitigation Rate'),
        ('compliance_score', 'Compliance Score'),
        ('quality_score', 'Quality Score'),
        ('efficiency_ratio', 'Efficiency Ratio'),
        ('milestone_completion_rate', 'Milestone Completion Rate'),
        ('change_request_frequency', 'Change Request Frequency'),
        ('vendor_performance', 'Vendor Performance'),
        ('contract_delivery_time', 'Contract Delivery Time'),
        ('bid_evaluation_time', 'Bid Evaluation Time'),
        ('specification_accuracy', 'Specification Accuracy'),
        ('tender_success_rate', 'Tender Success Rate'),
        ('cost_savings', 'Cost Savings'),
    ]
    
    METRIC_UNITS = [
        ('percentage', 'Percentage (%)'),
        ('currency', 'Currency'),
        ('days', 'Days'),
        ('hours', 'Hours'),
        ('count', 'Count'),
        ('ratio', 'Ratio'),
        ('score', 'Score (1-10)'),
        ('boolean', 'Yes/No'),
    ]
    
    STATUS_CHOICES = [
        ('on_target', 'On Target'),
        ('above_target', 'Above Target'),
        ('below_target', 'Below Target'),
        ('at_risk', 'At Risk'),
        ('critical', 'Critical'),
    ]
    
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('milestone', 'Per Milestone'),
        ('stage', 'Per Stage'),
        ('one_time', 'One Time'),
    ]

    # Core relationships
    procurement_plan = models.ForeignKey(
        'ProcurementPlan',
        related_name='performance_metrics',
        on_delete=models.CASCADE
    )
    
    # Metric definition
    metric_type = models.CharField(max_length=30, choices=METRIC_TYPES)
    metric_name = models.CharField(
        max_length=100,
        help_text="Custom name for this metric instance"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this metric measures"
    )
    unit = models.CharField(max_length=15, choices=METRIC_UNITS)
    
    # Values and targets
    current_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text="Current value of the metric"
    )
    target_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        help_text="Target value to achieve"
    )
    baseline_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Initial baseline value"
    )
    
    # Thresholds for status determination
    excellent_threshold = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Threshold for excellent performance"
    )
    good_threshold = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Threshold for good performance"
    )
    warning_threshold = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Threshold for warning status"
    )
    critical_threshold = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Threshold for critical status"
    )
    
    # Status and tracking
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='on_target')
    measurement_date = models.DateTimeField(default=timezone.now)
    frequency = models.CharField(max_length=15, choices=FREQUENCY_CHOICES, default='monthly')
    
    # Calculation details
    calculation_method = models.TextField(
        blank=True,
        help_text="Description of how this metric is calculated"
    )
    auto_calculated = models.BooleanField(
        default=False,
        help_text="Whether this metric is automatically calculated"
    )
    calculation_params = models.JSONField(
        default=dict,
        blank=True,
        help_text="Parameters used for automatic calculation"
    )
    
    # Ownership and responsibility
    owner = models.ForeignKey(
        CustomUser,
        related_name='owned_metrics',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User responsible for this metric"
    )
    measured_by = models.ForeignKey(
        CustomUser,
        related_name='measured_metrics',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who recorded this measurement"
    )
    
    # Additional context
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this measurement"
    )
    improvement_actions = models.TextField(
        blank=True,
        help_text="Actions being taken to improve this metric"
    )
    
    # Historical tracking
    previous_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Previous measurement value"
    )
    trend_direction = models.CharField(
        max_length=10,
        choices=[
            ('improving', 'Improving'),
            ('stable', 'Stable'),
            ('declining', 'Declining'),
            ('unknown', 'Unknown'),
        ],
        default='unknown'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    next_measurement_due = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the next measurement is due"
    )

    class Meta:
        ordering = ['-measurement_date', 'metric_type']
        verbose_name = "Performance Metric"
        verbose_name_plural = "Performance Metrics"
        indexes = [
            models.Index(fields=['procurement_plan', 'metric_type']),
            models.Index(fields=['measurement_date', 'status']),
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['next_measurement_due']),
        ]
        unique_together = ('procurement_plan', 'metric_type', 'measurement_date')

    def __str__(self):
        return f"{self.procurement_plan.policy_number} - {self.metric_name}: {self.current_value} {self.get_unit_display()}"

    def calculate_variance(self):
        """Calculate variance from target"""
        if self.target_value:
            return float(self.current_value - self.target_value)
        return 0

    def calculate_variance_percentage(self):
        """Calculate variance percentage from target"""
        if self.target_value and self.target_value != 0:
            variance = self.calculate_variance()
            return (variance / float(self.target_value)) * 100
        return 0

    def update_status(self):
        """Update status based on current value and thresholds"""
        value = float(self.current_value)
        
        # Determine if higher values are better or worse based on metric type
        higher_is_better = self.metric_type in [
            'budget_utilization', 'timeline_adherence', 'stakeholder_satisfaction',
            'compliance_score', 'quality_score', 'efficiency_ratio',
            'milestone_completion_rate', 'specification_accuracy', 'tender_success_rate'
        ]
        
        if self.excellent_threshold and self.critical_threshold:
            if higher_is_better:
                if value >= float(self.excellent_threshold):
                    self.status = 'above_target'
                elif value >= float(self.good_threshold or self.target_value):
                    self.status = 'on_target'
                elif value >= float(self.warning_threshold or self.target_value * Decimal('0.8')):
                    self.status = 'below_target'
                else:
                    self.status = 'critical'
            else:
                if value <= float(self.excellent_threshold):
                    self.status = 'above_target'
                elif value <= float(self.good_threshold or self.target_value):
                    self.status = 'on_target'
                elif value <= float(self.warning_threshold or self.target_value * Decimal('1.2')):
                    self.status = 'below_target'
                else:
                    self.status = 'critical'
        else:
            # Simple comparison with target
            variance_pct = abs(self.calculate_variance_percentage())
            if variance_pct <= 5:
                self.status = 'on_target'
            elif variance_pct <= 15:
                self.status = 'below_target'
            elif variance_pct <= 30:
                self.status = 'at_risk'
            else:
                self.status = 'critical'

    def update_trend(self):
        """Update trend direction based on previous value"""
        if self.previous_value:
            current = float(self.current_value)
            previous = float(self.previous_value)
            
            if current > previous:
                self.trend_direction = 'improving'
            elif current < previous:
                self.trend_direction = 'declining'
            else:
                self.trend_direction = 'stable'

    def get_status_color(self):
        """Get color code for status display"""
        colors = {
            'above_target': 'green',
            'on_target': 'blue',
            'below_target': 'yellow',
            'at_risk': 'orange',
            'critical': 'red',
        }
        return colors.get(self.status, 'gray')

    def get_trend_icon(self):
        """Get icon for trend direction"""
        icons = {
            'improving': '↗️',
            'stable': '→',
            'declining': '↘️',
            'unknown': '?',
        }
        return icons.get(self.trend_direction, '?')

    def calculate_next_measurement_date(self):
        """Calculate when the next measurement is due"""
        if self.frequency == 'daily':
            return self.measurement_date + timezone.timedelta(days=1)
        elif self.frequency == 'weekly':
            return self.measurement_date + timezone.timedelta(weeks=1)
        elif self.frequency == 'monthly':
            return self.measurement_date + timezone.timedelta(days=30)
        elif self.frequency == 'quarterly':
            return self.measurement_date + timezone.timedelta(days=90)
        else:
            return None

    def format_for_display(self):
        """Format metric for display in UI"""
        return {
            'id': self.id,
            'name': self.metric_name,
            'type': self.get_metric_type_display(),
            'current_value': float(self.current_value),
            'target_value': float(self.target_value),
            'unit': self.get_unit_display(),
            'status': self.get_status_display(),
            'status_color': self.get_status_color(),
            'variance': self.calculate_variance(),
            'variance_percentage': round(self.calculate_variance_percentage(), 2),
            'trend': self.get_trend_display(),
            'trend_icon': self.get_trend_icon(),
            'measurement_date': self.measurement_date,
            'next_due': self.next_measurement_due,
        }

    @classmethod
    def create_standard_metrics(cls, procurement_plan):
        """Create standard metrics for a procurement plan"""
        standard_metrics = [
            {
                'metric_type': 'cost_variance',
                'metric_name': 'Budget Variance',
                'unit': 'percentage',
                'target_value': Decimal('0'),
                'frequency': 'monthly',
            },
            {
                'metric_type': 'timeline_adherence',
                'metric_name': 'Schedule Adherence',
                'unit': 'percentage',
                'target_value': Decimal('95'),
                'frequency': 'weekly',
            },
            {
                'metric_type': 'milestone_completion_rate',
                'metric_name': 'Milestone Completion Rate',
                'unit': 'percentage',
                'target_value': Decimal('100'),
                'frequency': 'milestone',
            },
            {
                'metric_type': 'compliance_score',
                'metric_name': 'Compliance Score',
                'unit': 'score',
                'target_value': Decimal('8'),
                'frequency': 'quarterly',
            },
        ]
        
        metrics = []
        for metric_data in standard_metrics:
            metric = cls.objects.create(
                procurement_plan=procurement_plan,
                current_value=Decimal('0'),
                **metric_data
            )
            metrics.append(metric)
        
        return metrics

    @classmethod
    def get_overdue_measurements(cls, days_overdue=1):
        """Get metrics that are overdue for measurement"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days_overdue)
        return cls.objects.filter(
            next_measurement_due__lt=cutoff_date,
            next_measurement_due__isnull=False
        )

    def save(self, *args, **kwargs):
        # Store previous value for trend calculation
        if self.pk:
            try:
                old_instance = PerformanceMetric.objects.get(pk=self.pk)
                self.previous_value = old_instance.current_value
            except PerformanceMetric.DoesNotExist:
                pass
        
        # Update status and trend
        self.update_status()
        self.update_trend()
        
        # Calculate next measurement date
        if not self.next_measurement_due:
            self.next_measurement_due = self.calculate_next_measurement_date()
        
        super().save(*args, **kwargs)