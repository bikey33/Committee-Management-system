from django.db import models
from django.utils import timezone
from users.models import CustomUser


class ProcurementStakeholder(models.Model):
    """
    Track all stakeholders involved in procurement processes with their roles and responsibilities
    """
    
    STAKEHOLDER_ROLES = [
        ('owner', 'Project Owner'),
        ('manager', 'Procurement Manager'),
        ('technical_lead', 'Technical Lead'),
        ('financial_officer', 'Financial Officer'),
        ('legal_advisor', 'Legal Advisor'),
        ('committee_member', 'Committee Member'),
        ('committee_chair', 'Committee Chairperson'),
        ('evaluator', 'Bid Evaluator'),
        ('approver', 'Document Approver'),
        ('reviewer', 'Technical Reviewer'),
        ('coordinator', 'Project Coordinator'),
        ('vendor_liaison', 'Vendor Liaison'),
        ('compliance_officer', 'Compliance Officer'),
        ('quality_assurance', 'Quality Assurance'),
        ('stakeholder', 'General Stakeholder'),
        ('observer', 'Observer'),
    ]
    
    INVOLVEMENT_LEVELS = [
        ('primary', 'Primary - Core involvement'),
        ('secondary', 'Secondary - Supporting role'),
        ('consultant', 'Consultant - Advisory role'),
        ('reviewer', 'Reviewer - Review and approve'),
        ('observer', 'Observer - Information only'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending Assignment'),
        ('completed', 'Assignment Completed'),
    ]
    
    # Core relationships
    procurement_plan = models.ForeignKey(
        'ProcurementPlan',
        related_name='stakeholders',
        on_delete=models.CASCADE,
        help_text="The procurement plan this stakeholder is involved in"
    )
    user = models.ForeignKey(
        CustomUser,
        related_name='procurement_stakeholder_roles',
        on_delete=models.CASCADE,
        help_text="The user assigned as stakeholder"
    )
    
    # Stakeholder details
    role = models.CharField(
        max_length=30,
        choices=STAKEHOLDER_ROLES,
        help_text="Primary role of the stakeholder in this procurement"
    )
    involvement_level = models.CharField(
        max_length=15,
        choices=INVOLVEMENT_LEVELS,
        default='secondary',
        help_text="Level of involvement in the procurement process"
    )
    
    # Responsibilities and authority
    responsibilities = models.TextField(
        help_text="Detailed description of stakeholder's responsibilities and duties"
    )
    authority_level = models.CharField(
        max_length=20,
        choices=[
            ('view_only', 'View Only'),
            ('comment', 'Comment and Review'),
            ('approve', 'Approve Documents'),
            ('manage', 'Manage Process'),
            ('full_control', 'Full Control'),
        ],
        default='comment',
        help_text="Level of authority in the procurement process"
    )
    
    # Contact and communication preferences
    primary_contact = models.BooleanField(
        default=False,
        help_text="Is this the primary contact for this procurement?"
    )
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Notification preferences for different events"
    )
    contact_priority = models.IntegerField(
        default=5,
        help_text="Priority level for contact (1=highest, 10=lowest)"
    )
    
    # Assignment details
    assigned_by = models.ForeignKey(
        CustomUser,
        related_name='assigned_stakeholders',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who assigned this stakeholder role"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assignment_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When this stakeholder's involvement begins"
    )
    assignment_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="When this stakeholder's involvement ends"
    )
    
    # Status and activity tracking
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='active'
    )
    last_activity_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last date of any activity by this stakeholder"
    )
    
    # Performance and engagement metrics
    documents_reviewed = models.PositiveIntegerField(
        default=0,
        help_text="Number of documents reviewed by this stakeholder"
    )
    meetings_attended = models.PositiveIntegerField(
        default=0,
        help_text="Number of meetings attended"
    )
    approvals_given = models.PositiveIntegerField(
        default=0,
        help_text="Number of approvals provided"
    )
    
    # Additional metadata
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this stakeholder's involvement"
    )
    escalation_contact = models.ForeignKey(
        CustomUser,
        related_name='escalation_for_stakeholders',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Who to contact if this stakeholder is unavailable"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('procurement_plan', 'user', 'role')
        ordering = ['contact_priority', 'role', 'user__name']
        verbose_name = "Procurement Stakeholder"
        verbose_name_plural = "Procurement Stakeholders"
        indexes = [
            models.Index(fields=['procurement_plan', 'role']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['involvement_level', 'primary_contact']),
            models.Index(fields=['assigned_at', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.name or self.user.username} - {self.get_role_display()} ({self.procurement_plan.policy_number})"
    
    def save(self, *args, **kwargs):
        # Update last activity when status changes to active
        if self.status == 'active' and not self.last_activity_date:
            self.last_activity_date = timezone.now()
        
        # Ensure only one primary contact per procurement plan
        if self.primary_contact:
            ProcurementStakeholder.objects.filter(
                procurement_plan=self.procurement_plan,
                primary_contact=True
            ).exclude(pk=self.pk).update(primary_contact=False)
        
        super().save(*args, **kwargs)
    
    def get_responsibilities_list(self):
        """Return responsibilities as a list split by newlines"""
        if self.responsibilities:
            return [resp.strip() for resp in self.responsibilities.split('\n') if resp.strip()]
        return []
    
    def can_approve_documents(self):
        """Check if stakeholder has document approval authority"""
        return self.authority_level in ['approve', 'manage', 'full_control']
    
    def can_manage_process(self):
        """Check if stakeholder can manage the procurement process"""
        return self.authority_level in ['manage', 'full_control']
    
    def has_full_control(self):
        """Check if stakeholder has full control over the procurement"""
        return self.authority_level == 'full_control'
    
    def is_active_stakeholder(self):
        """Check if stakeholder is currently active"""
        if self.status != 'active':
            return False
        
        current_date = timezone.now().date()
        if self.assignment_start_date and current_date < self.assignment_start_date:
            return False
        if self.assignment_end_date and current_date > self.assignment_end_date:
            return False
        
        return True
    
    def get_involvement_summary(self):
        """Get a summary of stakeholder's involvement metrics"""
        return {
            'documents_reviewed': self.documents_reviewed,
            'meetings_attended': self.meetings_attended,
            'approvals_given': self.approvals_given,
            'involvement_level': self.get_involvement_level_display(),
            'authority_level': self.get_authority_level_display(),
            'days_involved': self.get_days_involved(),
        }
    
    def get_days_involved(self):
        """Calculate number of days involved in the procurement"""
        start_date = self.assignment_start_date or self.assigned_at.date()
        end_date = self.assignment_end_date or timezone.now().date()
        return (end_date - start_date).days
    
    def record_activity(self, activity_type=None, increment_counter=None):
        """Record stakeholder activity and update metrics"""
        self.last_activity_date = timezone.now()
        
        # Increment specific counters
        if increment_counter == 'documents_reviewed':
            self.documents_reviewed += 1
        elif increment_counter == 'meetings_attended':
            self.meetings_attended += 1
        elif increment_counter == 'approvals_given':
            self.approvals_given += 1
        
        self.save(update_fields=['last_activity_date', increment_counter] if increment_counter else ['last_activity_date'])
    
    def get_notification_preferences(self):
        """Get formatted notification preferences"""
        default_prefs = {
            'stage_changes': True,
            'document_uploads': True,
            'deadline_warnings': True,
            'meeting_invites': True,
            'approval_requests': True,
            'status_updates': False,
            'email_notifications': True,
            'sms_notifications': False,
        }
        return {**default_prefs, **self.notification_preferences}
    
    def set_notification_preference(self, preference_type, enabled):
        """Set a specific notification preference"""
        if not self.notification_preferences:
            self.notification_preferences = {}
        self.notification_preferences[preference_type] = enabled
        self.save(update_fields=['notification_preferences'])
    
    @classmethod
    def get_stakeholders_by_role(cls, procurement_plan, role):
        """Get all active stakeholders with a specific role"""
        return cls.objects.filter(
            procurement_plan=procurement_plan,
            role=role,
            status='active'
        ).select_related('user')
    
    @classmethod
    def get_primary_contacts(cls, procurement_plan):
        """Get all primary contacts for a procurement plan"""
        return cls.objects.filter(
            procurement_plan=procurement_plan,
            primary_contact=True,
            status='active'
        ).select_related('user')
    
    @classmethod
    def get_approvers(cls, procurement_plan):
        """Get all stakeholders who can approve documents"""
        return cls.objects.filter(
            procurement_plan=procurement_plan,
            authority_level__in=['approve', 'manage', 'full_control'],
            status='active'
        ).select_related('user')