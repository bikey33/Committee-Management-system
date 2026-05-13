
from django.db import models
from django.utils import timezone
from users.models import CustomUser


class ProcurementNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('success', 'Success'),
        ('reminder', 'Reminder'),
        ('approval_request', 'Approval Request'),
        ('approval_response', 'Approval Response'),
        ('deadline_alert', 'Deadline Alert'),
        ('status_change', 'Status Change'),
        ('milestone_reached', 'Milestone Reached'),
    ]
    
    # Core notification fields
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    
    # Recipient and relationships
    recipient = models.ForeignKey(
        CustomUser,
        related_name='notifications',
        on_delete=models.CASCADE
    )
    procurement_plan = models.ForeignKey(
        'ProcurementPlan',
        related_name='notifications',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    # Status tracking
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Procurement Notification'
        verbose_name_plural = 'Procurement Notifications'
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['procurement_plan', 'notification_type']),
            models.Index(fields=['sent_at', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.email}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read', 'updated_at'])
    
    def dismiss(self):
        """Dismiss notification"""
        if not self.dismissed_at:
            self.dismissed_at = timezone.now()
            self.save(update_fields=['dismissed_at', 'updated_at'])
    
    @property
    def is_dismissed(self):
        """Check if notification is dismissed"""
        return self.dismissed_at is not None
    
    @property
    def age_in_days(self):
        """Get age of notification in days"""
        return (timezone.now() - self.sent_at).days
    
    def get_type_color(self):
        """Get color for notification type"""
        colors = {
            'info': 'blue',
            'warning': 'yellow',
            'error': 'red',
            'success': 'green',
            'reminder': 'orange',
            'approval_request': 'purple',
            'approval_response': 'indigo',
            'deadline_alert': 'red',
            'status_change': 'blue',
            'milestone_reached': 'green',
        }
        return colors.get(self.notification_type, 'gray')
    
    @classmethod
    def create_notification(cls, recipient, title, message, notification_type='info', procurement_plan=None):
        """Create a new notification"""
        return cls.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            procurement_plan=procurement_plan
        )
    
    @classmethod
    def send_approval_request(cls, recipient, procurement_plan, approver_name):
        """Send approval request notification"""
        title = f"Approval Request: {procurement_plan.policy_number}"
        message = f"You have a new approval request for {procurement_plan.project_name} from {approver_name}."
        return cls.create_notification(
            recipient=recipient,
            title=title,
            message=message,
            notification_type='approval_request',
            procurement_plan=procurement_plan
        )
    
    @classmethod
    def send_deadline_alert(cls, recipient, procurement_plan, days_remaining):
        """Send deadline alert notification"""
        title = f"Deadline Alert: {procurement_plan.policy_number}"
        message = f"The procurement plan {procurement_plan.project_name} is due in {days_remaining} days."
        return cls.create_notification(
            recipient=recipient,
            title=title,
            message=message,
            notification_type='deadline_alert',
            procurement_plan=procurement_plan
        )
    
    @classmethod
    def send_status_change(cls, recipient, procurement_plan, old_status, new_status):
        """Send status change notification"""
        title = f"Status Update: {procurement_plan.policy_number}"
        message = f"The status of {procurement_plan.project_name} has changed from {old_status} to {new_status}."
        return cls.create_notification(
            recipient=recipient,
            title=title,
            message=message,
            notification_type='status_change',
            procurement_plan=procurement_plan
        )
