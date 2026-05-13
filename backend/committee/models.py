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

    class Meta:
        ordering = ['-created_at']  # Newest first (descending order)

    def __str__(self):
        return self.name


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
    committee = models.ForeignKey(Committee, related_name='memberships', on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    committee_role = models.CharField(max_length=50, default='member')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('committee', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.committee.name} ({self.committee_role})"


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
