from django.db import models
from django.utils import timezone


class ExternalIntegration(models.Model):
    """Model for tracking integrations with external systems"""
    
    SYNC_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
        ('maintenance', 'Maintenance'),
    ]
    
    system_name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the external system"
    )
    sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default='pending',
        help_text="Current synchronization status"
    )
    last_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last successful synchronization"
    )
    api_endpoint = models.URLField(
        blank=True,
        help_text="API endpoint for the external system"
    )
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Integration configuration settings"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Last error message if sync failed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'procurement_external_integration'
        ordering = ['system_name']
        verbose_name = 'External Integration'
        verbose_name_plural = 'External Integrations'
    
    def __str__(self):
        return f"{self.system_name} - {self.get_sync_status_display()}"
    
    def mark_sync_success(self):
        """Mark the integration as successfully synced"""
        self.sync_status = 'active'
        self.last_sync = timezone.now()
        self.error_message = ''
        self.save(update_fields=['sync_status', 'last_sync', 'error_message', 'updated_at'])
    
    def mark_sync_failed(self, error_message):
        """Mark the integration as failed with error message"""
        self.sync_status = 'failed'
        self.error_message = error_message
        self.save(update_fields=['sync_status', 'error_message', 'updated_at'])
    
    @property
    def is_active(self):
        """Check if the integration is currently active"""
        return self.sync_status == 'active'
    
    @property
    def sync_age_days(self):
        """Get the age of last sync in days"""
        if not self.last_sync:
            return None
        return (timezone.now() - self.last_sync).days