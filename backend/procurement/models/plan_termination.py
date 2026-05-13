from django.db import models
from users.models import CustomUser


class PlanTermination(models.Model):
    REASON_CATEGORIES = [
        ('project_cancelled', 'Project Cancellation'),
        ('funding_withdrawn', 'Funding Withdrawal'),
        ('legal_prohibition', 'Legal Prohibition'),
        ('no_responsive_bids', 'No Responsive Bids'),
        ('bids_above_budget', 'All Bids Above Budget'),
        ('irregularities', 'Irregularities Discovered'),
        ('public_interest', 'Public Interest'),
        ('other', 'Other'),
    ]

    procurement_plan = models.OneToOneField(
        'ProcurementPlan',
        related_name='termination',
        on_delete=models.CASCADE,
        help_text="The procurement plan that was terminated"
    )
    reason_category = models.CharField(
        max_length=30,
        choices=REASON_CATEGORIES,
        help_text="Categorized reason for termination"
    )
    reason = models.TextField(
        help_text="Detailed reason for termination"
    )
    remarks = models.TextField(
        blank=True,
        default='',
        help_text="Additional notes or remarks"
    )
    stage_at_termination = models.CharField(
        max_length=50,
        help_text="The stage the plan was at when terminated"
    )
    terminated_by = models.ForeignKey(
        CustomUser,
        related_name='terminated_plans',
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who terminated the plan"
    )
    terminated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the plan was terminated"
    )
    cascading_effects = models.JSONField(
        default=dict,
        blank=True,
        help_text="Summary of cascading effects applied during termination"
    )

    class Meta:
        verbose_name = "Plan Termination"
        verbose_name_plural = "Plan Terminations"
        ordering = ['-terminated_at']

    def __str__(self):
        return f"Termination of {self.procurement_plan.policy_number} - {self.get_reason_category_display()}"
