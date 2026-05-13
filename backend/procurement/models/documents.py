
import hashlib
from django.db import models
from django.utils import timezone
from users.models import CustomUser


class DocumentCategory(models.Model):
    """Dynamic document type/category that can be created at runtime."""
    key = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=100)
    max_file_size = models.PositiveIntegerField(default=10, help_text="Maximum file size in MB")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['label']
        verbose_name = 'Document Category'
        verbose_name_plural = 'Document Categories'

    def __str__(self):
        return self.label


class ProcurementDocument(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('needs_changes', 'Needs Changes'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived'),
        ('superseded', 'Superseded'),
    ]

    ACCESS_LEVEL_CHOICES = [
        ('public', 'Public'),
        ('internal', 'Internal'),
        ('restricted', 'Restricted'),
        ('confidential', 'Confidential'),
        ('classified', 'Classified'),
    ]
    
    # Core document fields
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    document_type = models.CharField(max_length=50)
    file = models.FileField(upload_to='procurement/documents/', blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    file_hash = models.CharField(max_length=64, blank=True)
    
    # Relationships
    procurement_plan = models.ForeignKey(
        'ProcurementPlan',
        related_name='documents',
        on_delete=models.CASCADE
    )
    uploaded_by = models.ForeignKey(
        CustomUser,
        related_name='uploaded_documents',
        on_delete=models.CASCADE
    )
    approved_by = models.ForeignKey(
        CustomUser,
        related_name='approved_documents',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    parent_document = models.ForeignKey(
        'self',
        related_name='versions',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Status and workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    version = models.CharField(max_length=20, default='1.0')
    version_number = models.CharField(max_length=20, default='1.0')
    version_notes = models.TextField(blank=True)
    is_current_version = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=False)
    approval_notes = models.TextField(blank=True)
    access_level = models.CharField(
        max_length=20,
        choices=ACCESS_LEVEL_CHOICES,
        default='internal'
    )
    allowed_roles = models.JSONField(default=list, blank=True)
    allowed_users = models.ManyToManyField(
        CustomUser,
        related_name='allowed_documents',
        blank=True
    )
    tags = models.JSONField(default=list, blank=True)
    custom_metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    last_accessed_by = models.ForeignKey(
        CustomUser,
        related_name='last_accessed_documents',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Procurement Document'
        verbose_name_plural = 'Procurement Documents'
        indexes = [
            models.Index(fields=['procurement_plan', 'document_type']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.procurement_plan.policy_number}"
    
    def get_file_extension(self):
        """Get file extension from file path"""
        if self.file_name:
            return self.file_name.split('.')[-1].lower()
        if self.file_path:
            return self.file_path.split('.')[-1].lower()
        if self.file and hasattr(self.file, 'name'):
            return self.file.name.split('.')[-1].lower()
        return ''
    
    def get_status_color(self):
        """Get color for document status"""
        colors = {
            'draft': 'gray',
            'review': 'yellow',
            'under_review': 'yellow',
            'approved': 'green',
            'rejected': 'red',
            'archived': 'blue',
            'superseded': 'purple',
        }
        return colors.get(self.status, 'gray')

    def get_access_level_display_color(self):
        colors = {
            'public': 'green',
            'internal': 'blue',
            'restricted': 'orange',
            'confidential': 'red',
            'classified': 'purple',
        }
        return colors.get(self.access_level, 'blue')

    def is_expired(self):
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    def can_access(self, user):
        if not user or not getattr(user, 'is_authenticated', False):
            return False

        if self.access_level == 'public':
            return True

        # Owner and uploader always can access
        if self.procurement_plan and self.procurement_plan.owner_id == user.pk:
            return True
        if self.uploaded_by_id == user.pk:
            return True

        # Explicit user allow list
        if self.allowed_users.filter(pk=user.pk).exists():
            return True

        # Role-based access
        user_role = getattr(user, 'user_role', None)
        role_name = user_role.name if user_role else None
        if role_name and role_name in (self.allowed_roles or []):
            return True

        # Internal docs: any authenticated user with a role
        if self.access_level == 'internal' and user_role:
            return True

        return False

    def record_access(self, user):
        """Record download/access statistics and user tracking."""
        self.last_accessed_by = user
        self.last_accessed_at = timezone.now()
        self.download_count += 1
        self.save()

    def _calculate_file_hash(self):
        if not self.file:
            return ''
        hasher = hashlib.sha256()
        for chunk in self.file.chunks():
            hasher.update(chunk)
        return hasher.hexdigest()

    def save(self, *args, **kwargs):
        if self.file:
            self.file_name = self.file.name.split('/')[-1]
            try:
                self.file_size = self.file.size
            except Exception:
                pass
            if not self.file_hash:
                try:
                    self.file_hash = self._calculate_file_hash()
                except Exception:
                    pass
        super().save(*args, **kwargs)


class DocumentAccessLog(models.Model):
    ACTION_TYPES = [
        ('view', 'Viewed'),
        ('download', 'Downloaded'),
        ('upload', 'Uploaded'),
        ('edit', 'Edited'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('share', 'Shared'),
    ]
    
    document = models.ForeignKey(
        ProcurementDocument,
        related_name='access_logs',
        on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        CustomUser,
        related_name='document_access_logs',
        on_delete=models.CASCADE
    )
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    additional_data = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Document Access Log'
        verbose_name_plural = 'Document Access Logs'
        indexes = [
            models.Index(fields=['document', 'timestamp']),
            models.Index(fields=['user', 'action']),
        ]
    
    def __str__(self):
        return f"{self.user.email} {self.action} {self.document.title}"


class DocumentApprovalWorkflow(models.Model):
    document = models.ForeignKey(
        ProcurementDocument,
        related_name='approval_workflows',
        on_delete=models.CASCADE
    )
    workflow_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Document Approval Workflow'
        verbose_name_plural = 'Document Approval Workflows'
    
    def __str__(self):
        return f"{self.workflow_name} - {self.document.title}"
    
    @property
    def is_completed(self):
        """Check if all approval steps are completed"""
        return all(step.status == 'approved' for step in self.steps.all())
    
    @property
    def current_step(self):
        """Get current approval step"""
        return self.steps.filter(status='pending').order_by('step_order').first()


class DocumentApprovalStep(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    workflow = models.ForeignKey(
        DocumentApprovalWorkflow,
        related_name='steps',
        on_delete=models.CASCADE
    )
    step_name = models.CharField(max_length=200)
    step_order = models.PositiveIntegerField()
    approver = models.ForeignKey(
        CustomUser,
        related_name='document_approval_steps',
        on_delete=models.CASCADE
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    comments = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['step_order']
        verbose_name = 'Document Approval Step'
        verbose_name_plural = 'Document Approval Steps'
        unique_together = ('workflow', 'step_order')
    
    def __str__(self):
        return f"{self.step_name} - {self.workflow.workflow_name}"
    
    def approve(self, comments=''):
        """Approve this step"""
        self.status = 'approved'
        self.comments = comments
        self.approved_at = timezone.now()
        self.save()
    
    def reject(self, comments=''):
        """Reject this step"""
        self.status = 'rejected'
        self.comments = comments
        self.save()
