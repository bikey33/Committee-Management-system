
from django.db import models
from django.utils import timezone
from users.models import CustomUser


class ApprovalWorkflow(models.Model):
    APPROVAL_TYPES = [
        ('technical', 'Technical Approval'),
        ('financial', 'Financial Approval'),
        ('management', 'Management Approval'),
        ('legal', 'Legal Approval'),
        ('procurement', 'Procurement Approval'),
        ('vendor', 'Vendor Approval'),
        ('contract', 'Contract Approval'),
        ('budget', 'Budget Approval'),
        ('specification', 'Specification Approval'),
        ('tender', 'Tender Approval'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    # Core relationships
    procurement_plan = models.ForeignKey(
        'ProcurementPlan',
        related_name='approval_workflows',
        on_delete=models.CASCADE
    )
    
    # Approval details
    approval_type = models.CharField(max_length=20, choices=APPROVAL_TYPES, default='technical')
    stage = models.CharField(max_length=100, help_text="Description of approval stage")
    sequence_order = models.PositiveIntegerField(default=1, help_text="Order in approval sequence")
    
    # Approver information
    approver = models.ForeignKey(
        CustomUser,
        related_name='approval_assignments',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User responsible for this approval"
    )
    backup_approver = models.ForeignKey(
        CustomUser,
        related_name='backup_approval_assignments',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Backup approver if primary is unavailable"
    )
    
    # Status and timeline
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField(null=True, blank=True)
    reviewed_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    
    # Approval details
    comments = models.TextField(blank=True, help_text="Comments from the approver")
    internal_notes = models.TextField(blank=True, help_text="Internal notes not visible to approver")
    
    # Conditions and requirements
    approval_conditions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of conditions that must be met for approval"
    )
    required_documents = models.JSONField(
        default=list,
        blank=True,
        help_text="List of documents required for this approval"
    )
    
    # Dependencies - using explicit through model
    depends_on = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        through='ApprovalWorkflowDependency',
        related_name='dependents',
        help_text="Other approvals that must be completed first"
    )
    
    # Delegation and escalation
    delegated_to = models.ForeignKey(
        CustomUser,
        related_name='delegated_approvals',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User this approval has been delegated to"
    )
    escalated_to = models.ForeignKey(
        CustomUser,
        related_name='escalated_approvals',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User this approval has been escalated to"
    )
    escalation_reason = models.TextField(blank=True)
    
    # Tracking
    reminder_sent_count = models.PositiveIntegerField(default=0)
    last_reminder_sent = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sequence_order', 'created_at']
        verbose_name = "Approval Workflow"
        verbose_name_plural = "Approval Workflows"
        unique_together = ('procurement_plan', 'approval_type', 'sequence_order')
        indexes = [
            models.Index(fields=['procurement_plan', 'status']),
            models.Index(fields=['approver', 'status']),
            models.Index(fields=['due_date', 'status']),
        ]

    def __str__(self):
        return f"{self.procurement_plan.policy_number} - {self.get_approval_type_display()} ({self.get_status_display()})"

    def is_overdue(self):
        """Check if approval is overdue"""
        if self.due_date and self.status in ['pending', 'in_review']:
            return timezone.now() > self.due_date
        return False

    def days_until_due(self):
        """Calculate days until due date"""
        if self.due_date and self.status in ['pending', 'in_review']:
            delta = self.due_date.date() - timezone.now().date()
            return delta.days
        return None

    def can_be_approved(self):
        """Check if all dependencies are satisfied"""
        return not self.depends_on.filter(status__in=['pending', 'in_review']).exists()

    def get_effective_approver(self):
        """Get the effective approver (considering delegation/escalation)"""
        if self.escalated_to:
            return self.escalated_to
        elif self.delegated_to:
            return self.delegated_to
        else:
            return self.approver

    def approve(self, user, comments=''):
        """Approve this workflow step"""
        if not self.can_be_approved():
            raise ValueError("Cannot approve: dependencies not satisfied")
        
        self.status = 'approved'
        self.comments = comments
        self.completed_date = timezone.now()
        self.reviewed_date = timezone.now()
        self.save()
        
        # Trigger next approval if this was a dependency
        self._trigger_dependent_approvals()

    def reject(self, user, comments=''):
        """Reject this workflow step"""
        self.status = 'rejected'
        self.comments = comments
        self.completed_date = timezone.now()
        self.reviewed_date = timezone.now()
        self.save()

    def delegate(self, delegated_to, user, reason=''):
        """Delegate approval to another user"""
        self.delegated_to = delegated_to
        self.internal_notes += f"\nDelegated to {delegated_to.username} by {user.username}: {reason}"
        self.save()

    def escalate(self, escalated_to, user, reason=''):
        """Escalate approval to another user"""
        self.escalated_to = escalated_to
        self.escalation_reason = reason
        self.internal_notes += f"\nEscalated to {escalated_to.username} by {user.username}: {reason}"
        self.save()

    def send_reminder(self):
        """Record that a reminder was sent"""
        self.reminder_sent_count += 1
        self.last_reminder_sent = timezone.now()
        self.save()

    def _trigger_dependent_approvals(self):
        """Trigger approvals that were waiting for this one"""
        dependent_approvals = ApprovalWorkflow.objects.filter(
            depends_on=self,
            status='pending'
        )
        
        for approval in dependent_approvals:
            if approval.can_be_approved():
                approval.status = 'in_review'
                approval.save()

    def save(self, *args, **kwargs):
        # Auto-update reviewed_date when status changes to in_review
        if self.status == 'in_review' and not self.reviewed_date:
            self.reviewed_date = timezone.now()
        
        super().save(*args, **kwargs)


class ApprovalWorkflowDependency(models.Model):
    """Model to handle many-to-many dependencies between approval workflows"""
    from_workflow = models.ForeignKey(
        'ApprovalWorkflow',
        on_delete=models.CASCADE,
        related_name='dependency_sources'
    )
    to_workflow = models.ForeignKey(
        'ApprovalWorkflow',
        on_delete=models.CASCADE,
        related_name='dependency_targets'
    )

    class Meta:
        unique_together = ('from_workflow', 'to_workflow')
        verbose_name = "Approval Workflow Dependency"
        verbose_name_plural = "Approval Workflow Dependencies"

    def __str__(self):
        return f"{self.from_workflow} depends on {self.to_workflow}"
