
# backend/users/models.py
import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, employee_id, email, password=None, **extra_fields):
        if not employee_id:
            raise ValueError('The Employee ID field must be set')
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        extra_fields.setdefault('username', employee_id)
        user = self.model(employee_id=employee_id, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, employee_id, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(employee_id, email, password, **extra_fields)





class Position(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=150)
    level = models.IntegerField(default=0)
    alias = models.CharField(max_length=100, null=True, blank=True)
    post_alias = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        db_table = 'users_position'
        ordering = ['-level', 'name']
        
    def __str__(self):
        return f"{self.name} ({self.level})"

# ---------------------------------------------------------------------------
# NEW RBAC: Role, Permission, RolePermission
# ---------------------------------------------------------------------------

class Permission(models.Model):
    """
    Registry of all application-level permissions.
    Seeded by seed_rbac.py — one row per operation in the codebase.
    """
    GROUP_CHOICES = [
        ('user_management', 'User Management'),
        ('settings',        'System Settings'),
        ('planning',        '1. Planning'),
        ('specification',   '2. Specification'),
        ('spec_review',     '3. Specification Review'),
        ('tender',          '4. Tender'),
        ('evaluation',      '5. Evaluation'),
        ('letters',         '6. LOI / LOA'),
        ('contract',        '7. Contract Preparation'),
        ('bidding',         '8. Bidders & Bids'),
        ('reports',         'Reports & Analytics'),
        ('committee',       'Committee Management'),
    ]

    codename    = models.CharField(max_length=100, unique=True)   # e.g. 'procurement_plan.create'
    name        = models.CharField(max_length=200)                # e.g. 'Create Procurement Plan'
    group       = models.CharField(max_length=50, choices=GROUP_CHOICES)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        db_table = 'users_permission'
        ordering = ['group', 'name']

    def __str__(self):
        return f"[{self.group}] {self.codename}"


class Role(models.Model):
    """
    Named functional role created and managed by Super Admin.
    A role bundles a set of permissions via RolePermission.
    """
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_role'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_permissions(self) -> list:
        """Return list of active permission codenames for this role."""
        return list(
            self.role_permissions
                .filter(is_active=True)
                .values_list('permission__codename', flat=True)
        )

    def get_permission_objects(self):
        """Return Permission QuerySet for this role."""
        return Permission.objects.filter(
            role_permissions__role=self,
            role_permissions__is_active=True,
        )


class RolePermission(models.Model):
    """
    Join table binding a Role to a Permission.
    Includes audit trail: who granted it and when.
    """
    role        = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name='role_permissions'
    )
    permission  = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name='role_permissions'
    )
    is_active   = models.BooleanField(default=True)
    granted_at  = models.DateTimeField(auto_now_add=True)
    granted_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='granted_permissions',
    )

    class Meta:
        db_table = 'users_rolepermission'
        unique_together = ('role', 'permission')
        ordering = ['role', 'permission__group', 'permission__name']

    def __str__(self):
        return f"{self.role.name} → {self.permission.codename}"


class Directorate(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_directorate'
        ordering = ['name']

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)
    directorate = models.ForeignKey(
        Directorate, on_delete=models.SET_NULL, null=True, blank=True, related_name='departments'
    )
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_department'
        ordering = ['name']

    def __str__(self):
        return self.name


class Office(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    directorate = models.ForeignKey(
        Directorate, on_delete=models.SET_NULL, null=True, blank=True, related_name='offices'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users_procurement_office'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def directorate_name(self):
        if self.directorate:
            return self.directorate.name
        return None


class WorkingOffice(models.Model):
    name_of_office = models.CharField(max_length=255)
    directorate_id = models.IntegerField(null=True, blank=True)
    ac_office_id = models.IntegerField(null=True, blank=True)
    cc_office_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'users_working_office'
        ordering = ['name_of_office']
        managed = False

    def __str__(self):
        return self.name_of_office


class ErpEmployeeRecord(models.Model):
    """
    Read-only mapping onto the raw ERP import table `employee_erp_record_master`.

    This is a staging/source table imported from an external ERP. Django never
    creates, migrates, or drops it (managed = False); it exists only so the
    `sync_erp_employees` command can read it through the ORM and upsert rows
    into EmployeeDetail (the app's working employee directory).
    """
    empno          = models.CharField(max_length=30, null=True, blank=True)
    title          = models.CharField(max_length=30, null=True, blank=True)
    first_name     = models.CharField(max_length=150, null=True, blank=True)
    middle_names   = models.CharField(max_length=60, null=True, blank=True)
    last_name      = models.CharField(max_length=150, null=True, blank=True)
    dob            = models.DateField(null=True, blank=True)
    sex            = models.CharField(max_length=80, null=True, blank=True)
    grade          = models.CharField(max_length=240, null=True, blank=True)
    seniority_date = models.DateField(null=True, blank=True)
    job_id         = models.DecimalField(max_digits=15, decimal_places=0, null=True, blank=True)
    job_name       = models.CharField(max_length=700, null=True, blank=True)
    work_org_id    = models.CharField(max_length=150, null=True, blank=True)
    work_office    = models.CharField(max_length=240, null=True, blank=True)
    mobile         = models.CharField(max_length=60, null=True, blank=True)
    email_address  = models.CharField(max_length=240, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'employee_erp_record_master'
        ordering = ['empno']

    def __str__(self):
        return self.empno or f"erp#{self.pk}"


# ---------------------------------------------------------------------------
# CustomUser
# ---------------------------------------------------------------------------


class CustomUser(AbstractUser):
    _id         = models.CharField(max_length=100, unique=True, blank=True)
    employee_id = models.CharField(max_length=10, unique=True, primary_key=True)
    email       = models.EmailField(unique=True)
    # Lightweight authentication/profile linkage only. Business data moved to EmployeeDetail.
    # RBAC and Office hierarchy (keep office reference for permission scoping)
    office = models.ForeignKey(
        Office, on_delete=models.SET_NULL, null=True, blank=True, related_name='users'
    )

    # New RBAC role FK
    user_role   = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='users',
        db_column='user_role_id',
    )

    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    otp_enabled = models.BooleanField(default=False)
    # Set when an account is provisioned with a system-generated password
    # (e.g. self-service signup); forces a password change on first login.
    must_change_password = models.BooleanField(default=False)
    reset_token = models.CharField(max_length=100, blank=True)
    last_login  = models.DateTimeField(blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD  = 'employee_id'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table = 'users_customuser'

    def __str__(self):
        return self.employee_id

    def save(self, *args, **kwargs):
        if not self._id:
            self._id = str(uuid.uuid4())
        if not self.username or self.username != self.employee_id:
            self.username = self.employee_id
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # RBAC helpers
    # ------------------------------------------------------------------

    def get_permission_codenames(self) -> list:
        """Return list of permission codenames from the assigned Role."""
        if not self.user_role_id:
            return []
        return self.user_role.get_permissions()

    def has_rbac_permission(self, codename: str) -> bool:
        """Check whether this user's role includes the given permission."""
        return codename in self.get_permission_codenames()

    def is_super_admin(self) -> bool:
        """True if Django superuser flag is set, or role name is any variant of 'Super Admin'."""
        if self.is_superuser:
            return True
        if self.user_role:
            normalized = self.user_role.name.lower().replace(' ', '')
            return normalized == 'superadmin'
        return False


# ---------------------------------------------------------------------------
# Supporting models (unchanged)
# ---------------------------------------------------------------------------

class PermissionAuditLog(models.Model):
    ACTION_CHOICES = [
        ('added',       'Added'),
        ('removed',     'Removed'),
        ('modified',    'Modified'),
        ('bulk_update', 'Bulk Update'),
    ]

    role            = models.ForeignKey(Role, on_delete=models.CASCADE,
                                         related_name='permission_audit_logs')
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                         null=True, blank=True)
    action          = models.CharField(max_length=20, choices=ACTION_CHOICES)
    permission      = models.CharField(max_length=100)
    old_permissions = models.JSONField(default=list, blank=True)
    new_permissions = models.JSONField(default=list, blank=True)
    details         = models.TextField(blank=True)
    timestamp       = models.DateTimeField(auto_now_add=True)
    ip_address      = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']


class ModuleAccess(models.Model):
    module       = models.CharField(max_length=50, unique=True)
    permissions  = models.JSONField(default=list)
    restricted_to = models.JSONField(default=list)

    def __str__(self):
        return self.module


class OTPLog(models.Model):
    STATUS_CHOICES = [
        ('sent',         'Sent'),
        ('verified',     'Verified'),
        ('failed',       'Failed'),
        ('expired',      'Expired'),
        ('invalidated',  'Invalidated'),
    ]
    PURPOSE_CHOICES = [
        ('login',           'Login'),
        ('password_reset',  'Password Reset'),
    ]

    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name='otp_logs')
    phone      = models.CharField(max_length=15)
    seq_no     = models.CharField(max_length=50)
    purpose    = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='login')
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    attempts   = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', 'created_at']),
            models.Index(fields=['seq_no']),
        ]

    def __str__(self):
        return f"OTP for {self.user_id} - {self.status} ({self.seq_no})"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @property
    def is_active(self):
        return self.status == 'sent' and not self.is_expired


class EmployeeDetail(models.Model):
    employee_id   = models.CharField(max_length=10, unique=True, primary_key=True)
    user          = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_profile',
        null=True,
        blank=True,
    )

    # Business / domain fields
    name          = models.CharField(max_length=150, blank=True, null=True)
    email         = models.EmailField(unique=True, null=True, blank=True)
    phone         = models.CharField(max_length=15, blank=True, null=True)
    # keep position as free text to avoid tight coupling; can be converted to FK later
    position      = models.CharField(max_length=100, blank=True, null=True)
    level         = models.CharField(max_length=10, blank=True, null=True)
    service       = models.CharField(max_length=50, blank=True, null=True)
    group         = models.CharField(max_length=50, blank=True, null=True)
    qualification = models.TextField(blank=True, null=True)
    seniority     = models.DateTimeField(blank=True, null=True)
    retirement    = models.DateTimeField(blank=True, null=True)
    mno           = models.CharField(max_length=15, blank=True, null=True)
    department    = models.CharField(max_length=50, blank=True, null=True)
    designation   = models.CharField(max_length=100, blank=True, null=True, default='Engineer')

    def __str__(self):
        return self.employee_id
