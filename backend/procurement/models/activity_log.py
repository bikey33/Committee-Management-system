from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from users.models import CustomUser


class ActivityLog(models.Model):
    ACTION_TYPES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('deleted', 'Deleted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
        ('assigned', 'Assigned'),
        ('unassigned', 'Unassigned'),
        ('delegated', 'Delegated'),
        ('escalated', 'Escalated'),
        ('stage_advanced', 'Stage Advanced'),
        ('stage_reverted', 'Stage Reverted'),
        ('status_changed', 'Status Changed'),
        ('document_uploaded', 'Document Uploaded'),
        ('document_downloaded', 'Document Downloaded'),
        ('document_deleted', 'Document Deleted'),
        ('comment_added', 'Comment Added'),
        ('comment_updated', 'Comment Updated'),
        ('comment_deleted', 'Comment Deleted'),
        ('milestone_completed', 'Milestone Completed'),
        ('risk_identified', 'Risk Identified'),
        ('risk_mitigated', 'Risk Mitigated'),
        ('stakeholder_added', 'Stakeholder Added'),
        ('stakeholder_removed', 'Stakeholder Removed'),
        ('timeline_adjusted', 'Timeline Adjusted'),
        ('budget_modified', 'Budget Modified'),
        ('specification_updated', 'Specification Updated'),
        ('tender_published', 'Tender Published'),
        ('bid_received', 'Bid Received'),
        ('committee_formed', 'Committee Formed'),
        ('evaluation_started', 'Evaluation Started'),
        ('evaluation_completed', 'Evaluation Completed'),
        ('contract_awarded', 'Contract Awarded'),
        ('notification_sent', 'Notification Sent'),
        ('meeting_scheduled', 'Meeting Scheduled'),
        ('meeting_completed', 'Meeting Completed'),
        ('system_action', 'System Action'),
        ('plan_terminated', 'Plan Terminated'),
    ]
    
    SEVERITY_LEVELS = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]

    # Core relationships
    procurement_plan = models.ForeignKey(
        'ProcurementPlan',
        related_name='activity_logs',
        on_delete=models.CASCADE,
        help_text="The procurement plan this activity relates to"
    )
    
    # Activity details
    action = models.CharField(max_length=30, choices=ACTION_TYPES)
    action_description = models.CharField(
        max_length=255,
        help_text="Human-readable description of the action"
    )
    
    # User information
    user = models.ForeignKey(
        CustomUser,
        related_name='activity_logs',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who performed the action (null for system actions)"
    )
    user_display_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Display name of user at time of action"
    )
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Activity context
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional details about the activity"
    )
    
    # Related object (generic foreign key for flexibility)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Type of related object"
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="ID of related object"
    )
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional metadata
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS,
        default='info'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of user who performed action"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string from browser"
    )
    
    # Changes tracking
    old_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="Previous values before the change"
    )
    new_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="New values after the change"
    )
    
    # System information
    is_system_action = models.BooleanField(
        default=False,
        help_text="Whether this was an automated system action"
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        help_text="Session key for grouping related actions"
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        indexes = [
            models.Index(fields=['procurement_plan', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        user_info = self.user_display_name or (self.user.username if self.user else 'System')
        return f"{self.procurement_plan.policy_number} - {user_info}: {self.action_description}"

    @classmethod
    def log_activity(cls, procurement_plan, action, user=None, description=None, 
                    details=None, related_object=None, severity='info',
                    old_values=None, new_values=None, ip_address=None, user_agent=None):
        """
        Create a new activity log entry
        
        Args:
            procurement_plan: ProcurementPlan instance
            action: Action type from ACTION_TYPES
            user: User who performed the action (optional for system actions)
            description: Human-readable description
            details: Dictionary of additional details
            related_object: Related model instance (optional)
            severity: Severity level
            old_values: Dictionary of old values for updates
            new_values: Dictionary of new values for updates
            ip_address: IP address of the user
            user_agent: User agent string
        """
        # Generate description if not provided
        if not description:
            action_display = dict(cls.ACTION_TYPES).get(action, action)
            description = f"{action_display} on {procurement_plan.policy_number}"
        
        # Get content type and object ID for related object
        content_type = None
        object_id = None
        if related_object:
            content_type = ContentType.objects.get_for_model(related_object)
            object_id = related_object.pk
        
        # Create the log entry
        log_entry = cls.objects.create(
            procurement_plan=procurement_plan,
            action=action,
            action_description=description,
            user=user,
            user_display_name=user.get_full_name() if user else 'System',
            details=details or {},
            content_type=content_type,
            object_id=object_id,
            severity=severity,
            old_values=old_values or {},
            new_values=new_values or {},
            is_system_action=user is None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return log_entry

    def get_changes_summary(self):
        """Get a summary of what changed in this activity"""
        if not self.old_values and not self.new_values:
            return None
        
        changes = []
        all_keys = set(self.old_values.keys()) | set(self.new_values.keys())
        
        for key in all_keys:
            old_val = self.old_values.get(key, 'N/A')
            new_val = self.new_values.get(key, 'N/A')
            
            if old_val != new_val:
                changes.append({
                    'field': key,
                    'old_value': old_val,
                    'new_value': new_val
                })
        
        return changes

    def get_severity_color(self):
        """Get color code for severity display"""
        colors = {
            'info': 'blue',
            'warning': 'yellow',
            'error': 'red',
            'critical': 'purple',
        }
        return colors.get(self.severity, 'gray')

    def format_for_display(self):
        """Format activity log for display in UI"""
        return {
            'id': self.id,
            'action': self.get_action_display(),
            'description': self.action_description,
            'user': self.user_display_name,
            'timestamp': self.timestamp,
            'severity': self.get_severity_display(),
            'severity_color': self.get_severity_color(),
            'details': self.details,
            'changes': self.get_changes_summary(),
            'is_system_action': self.is_system_action,
        }

    @classmethod
    def get_recent_activities(cls, procurement_plan, limit=50):
        """Get recent activities for a procurement plan"""
        return cls.objects.filter(
            procurement_plan=procurement_plan
        ).select_related('user')[:limit]

    @classmethod
    def get_user_activities(cls, user, limit=100):
        """Get recent activities by a specific user"""
        return cls.objects.filter(
            user=user
        ).select_related('procurement_plan')[:limit]

    @classmethod
    def get_activities_by_action(cls, procurement_plan, action_type):
        """Get all activities of a specific type for a procurement plan"""
        return cls.objects.filter(
            procurement_plan=procurement_plan,
            action=action_type
        ).select_related('user')

    @classmethod
    def get_critical_activities(cls, procurement_plan):
        """Get critical and error activities for a procurement plan"""
        return cls.objects.filter(
            procurement_plan=procurement_plan,
            severity__in=['critical', 'error']
        ).select_related('user')

    def save(self, *args, **kwargs):
        # Set user display name if not provided
        if self.user and not self.user_display_name:
            self.user_display_name = self.user.get_full_name() or self.user.username
        
        super().save(*args, **kwargs)