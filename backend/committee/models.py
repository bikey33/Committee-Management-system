# committee/models.py
from django.db import models
from users.models import CustomUser
from procurement.models import ProcurementPlan
from django.utils import timezone


class Committee(models.Model):
    COMMITTEE_TYPES = [
        ('specification', 'Specification'),
        ('evaluation', 'Evaluation'),
        ('review', 'Review'),
        ('contract', 'Contract'),
        ('other', 'Other'),
    ]

    COMMITTEE_STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('active', 'Active'),
        ('under_review', 'Under Review'),
        ('completed', 'Completed'),
        ('suspended', 'Suspended'),
        ('dissolved', 'Dissolved'),
    ]

    name = models.CharField(max_length=255)
    purpose = models.TextField()
    committee_type = models.CharField(max_length=50, choices=COMMITTEE_TYPES)

    # Use string reference to avoid circular import
    procurement_plan = models.ForeignKey(
        'procurement.ProcurementPlan',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='committees'
    )

    office = models.ForeignKey(
        'users.Office',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='committees'
    )

    formation_date = models.DateField(null=True, blank=True)
    specification_submission_date = models.DateField(null=True, blank=True)
    review_date = models.DateField(null=True, blank=True)
    schedule = models.TextField(null=True, blank=True)
    should_notify = models.BooleanField(default=False)
    formation_letter = models.FileField(upload_to='formation_letters/', null=True, blank=True)
    approval_status = models.CharField(max_length=50, default='active')

    # Enhanced committee lifecycle tracking fields
    assigned_date = models.DateField(
        null=True, blank=True, help_text="Date when committee was assigned to procurement plan")
    completion_date = models.DateField(null=True, blank=True, help_text="Date when committee completed their work")
    technical_evaluation_completion_date = models.DateField(null=True, blank=True, help_text="Date when technical evaluation was completed")
    financial_evaluation_completion_date = models.DateField(null=True, blank=True, help_text="Date when financial evaluation was completed")
    decision_date = models.DateField(null=True, blank=True, help_text="Date when final committee decision was reached")
    committee_status = models.CharField(
        max_length=20,
        choices=COMMITTEE_STATUS_CHOICES,
        default='assigned',
        help_text="Current status of the committee in its lifecycle"
    )

    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_committees')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deadline = models.DateField(null=True, blank=True)
    specification_title = models.CharField(max_length=255, blank=True, null=True)
    specification_description = models.TextField(blank=True, null=True)
    
    # Phase management
    current_phase = models.CharField(
        max_length=20,
        choices=[
            ('initialization', 'Initialization'),
            ('finalization', 'Finalization'),
        ],
        default='initialization',
        help_text="Current phase of the committee lifecycle"
    )

    class Meta:
        ordering = ['-created_at']  # Newest first (descending order)

    def __str__(self):
        return self.name
    
    def get_phase_progress(self):
        """Get progress information for current and all phases"""
        phases = {
            'initialization': {
                'name': 'Initialization',
                'order': 1,
                'completed': self.initialization_phase_completed,
                'checkpoints': list(self.checkpoints.filter(phase='initialization').order_by('order'))
            },
            'finalization': {
                'name': 'Finalization',
                'order': 2,
                'completed': self.finalization_phase_completed,
                'checkpoints': list(self.checkpoints.filter(phase='finalization').order_by('order')),
                'visible': self.initialization_phase_completed
            }
        }
        return phases
    
    @property
    def initialization_phase_completed(self):
        """Check if all initialization checkpoints are completed"""
        checkpoints = self.checkpoints.filter(phase='initialization')
        if not checkpoints.exists():
            return False
        return all(cp.is_completed for cp in checkpoints)
    
    @property
    def finalization_phase_completed(self):
        """Check if all finalization checkpoints are completed"""
        checkpoints = self.checkpoints.filter(phase='finalization')
        if not checkpoints.exists():
            return False
        return all(cp.is_completed for cp in checkpoints)


class CommitteeRole(models.Model):
    value = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "label"]

    def __str__(self):
        return self.label


class CommitteeMembership(models.Model):
    """A user's membership in a committee.

    Soft-deleted (is_active=False, left_at set) on removal so 'past committees'
    history is retained. One row per (committee, user): re-adding reactivates the
    existing row, so only the latest join/leave stint is tracked (full multi-stint
    history would be a separate additive audit table).
    """
    committee = models.ForeignKey(Committee, related_name='memberships', on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    committee_role = models.CharField(max_length=50, default='member')
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('committee', 'user')
        indexes = [
            models.Index(fields=['committee', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.committee.name} ({self.committee_role})"

    def reactivate(self, role=None):
        """Re-activate a previously-removed membership (a fresh join)."""
        self.is_active = True
        self.left_at = None
        self.created_at = timezone.now()
        if role is not None:
            self.committee_role = role
        self.save(update_fields=['is_active', 'left_at', 'created_at', 'committee_role'])

    def soft_delete(self):
        """Mark the membership as removed while retaining history."""
        self.is_active = False
        self.left_at = timezone.now()
        self.save(update_fields=['is_active', 'left_at'])


def is_committee_closed(committee) -> bool:
    """Single source of truth for 'closed' (mirrors the frontend CommitteeStepper)."""
    if committee.committee_status in ('completed', 'dissolved'):
        return True
    return bool(committee.finalization_phase_completed)


def is_committee_overdue(committee) -> bool:
    if is_committee_closed(committee):
        return False
    return bool(committee.deadline) and committee.deadline < timezone.localdate()


class ReviewCommitteeDefaultMember(models.Model):
    """Default members that are automatically added to every review committee upon creation."""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='default_review_memberships'
    )
    committee_role = models.CharField(max_length=50, default='member')
    office = models.ForeignKey(
        'users.Office',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='default_review_members',
        help_text="If set, this default applies only to the specified office (and its subtree). If null, it is a global fallback."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'committee_role', 'office')
        ordering = ['committee_role', 'created_at']

    def __str__(self):
        office_label = self.office.name if self.office else "Global"
        return f"{self.user.username} - {self.committee_role} ({office_label})"


class CommitteePhaseCheckpoint(models.Model):
    """Tracks checkpoints/milestones in each phase of a committee's lifecycle"""
    
    PHASE_CHOICES = [
        ('initialization', 'Initialization'),
        ('finalization', 'Finalization'),
    ]
    
    committee = models.ForeignKey(
        Committee,
        on_delete=models.CASCADE,
        related_name='checkpoints'
    )
    phase = models.CharField(
        max_length=20,
        choices=PHASE_CHOICES,
        help_text="Which phase this checkpoint belongs to"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_date = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_checkpoints'
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['phase', 'order', 'created_at']
        unique_together = ('committee', 'phase', 'order')
        indexes = [
            models.Index(fields=['committee', 'phase']),
            models.Index(fields=['committee', 'is_completed']),
        ]
    
    def __str__(self):
        return f"{self.committee.name} - {self.get_phase_display()} - {self.name}"
    
    def mark_completed(self, user=None):
        """Mark checkpoint as completed"""
        from django.utils import timezone
        self.is_completed = True
        self.completed_date = timezone.now()
        self.completed_by = user
        self.save()
