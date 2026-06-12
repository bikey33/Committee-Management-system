# backend/users/serializers.py
from rest_framework import serializers
from django.db import transaction
from django.contrib.auth.hashers import make_password
import secrets
import string
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CustomUser, EmployeeDetail, ErpEmployeeRecord, PermissionAuditLog, OTPLog, Role, Permission, RolePermission, Directorate, Office, Department, Position, WorkingOffice

class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = '__all__'

class RobustPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def to_internal_value(self, data):
        if self.pk_field is not None:
            data = self.pk_field.to_internal_value(data)
        try:
            # Use .filter().first() instead of .get() to handle external views with duplicate IDs
            obj = self.get_queryset().filter(pk=data).first()
            if obj is None:
                self.fail('does_not_exist', pk_value=data)
            return obj
        except (TypeError, ValueError):
            self.fail('incorrect_type', data_type=type(data).__name__)
from .tasks import send_welcome_email
from utils.ntc_otp import send_otp as ntc_send_otp
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def get_employee_profile(user):
    return getattr(user, 'employee_profile', None)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    employee_id = serializers.CharField()  # Input field for employee_id or email

    def validate(self, attrs):
        identifier = attrs.get('employee_id')
        password = attrs.get('password')
        user = None

        try:
            user = User.objects.get(employee_id=identifier)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=identifier)
            except User.DoesNotExist:
                raise serializers.ValidationError('No active account found with the given credentials')

        credentials = {'employee_id': user.employee_id, 'password': password}
        user = authenticate(request=self.context.get('request'), **credentials)

        if not user:
            raise serializers.ValidationError('No active account found with the given credentials')

        # Check if OTP is enabled for this user
        if user.otp_enabled:
            profile = get_employee_profile(user)
            phone_number = getattr(profile, 'phone', None) or getattr(profile, 'mno', None)
            if not phone_number:
                logger.error(f"OTP enabled but no phone number for user {user.employee_id}")
                raise serializers.ValidationError(
                    'OTP is enabled but no phone number is registered. Please contact admin.'
                )

            # Send OTP via NTC service
            otp_result = ntc_send_otp(phone_number)

            if not otp_result['success']:
                logger.error(f"Failed to send OTP to {user.employee_id}: {otp_result['error']}")
                raise serializers.ValidationError(
                    'Failed to send OTP. Please try again later.'
                )

            # Get client IP
            request = self.context.get('request')
            ip_address = None
            if request:
                forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
                ip_address = forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')

            # Invalidate any previous active OTPs for this user
            OTPLog.objects.filter(
                user=user, status='sent'
            ).update(status='invalidated')

            # Create OTP log entry
            expiry_minutes = int(getattr(
                __import__('django.conf', fromlist=['settings']).settings,
                'OTP_EXPIRY_MINUTES', 5
            ))
            OTPLog.objects.create(
                user=user,
                phone=phone_number,
                seq_no=otp_result['transaction_id'],
                purpose='login',
                status='sent',
                ip_address=ip_address,
                expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
            )

            # Mask phone number for frontend display
            phone_hint = f"***{phone_number[-4:]}" if len(phone_number) >= 4 else "***"

            # Return OTP-required response (no tokens issued)
            raise serializers.ValidationError({
                'otp_required': True,
                'user_id': user.employee_id,
                'phone_hint': phone_hint,
                'detail': 'OTP sent to your registered phone number.',
            })

        # If no OTP needed, continue normal login flow
        data = super().validate(attrs)
        refresh = self.get_token(user)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        data['user'] = {
            '_id': user._id,
            'name': self.get_full_name(user),
            'email': user.email,
            'employeeId': user.employee_id,
            'user_role': {
                'id': user.user_role.id,
                'name': user.user_role.name,
                'description': user.user_role.description,
                'permissions': user.get_permission_codenames(),
            } if user.user_role_id else None,
            'department': getattr(get_employee_profile(user), 'department', None),
            'phoneNumber': getattr(get_employee_profile(user), 'phone', None) or getattr(get_employee_profile(user), 'mno', None),
            'designation': getattr(get_employee_profile(user), 'designation', None),
            'isActive': user.is_active,
            'otpEnabled': user.otp_enabled,
            'mustChangePassword': user.must_change_password,
            'office': {
                'id': user.office.id,
                'name': user.office.name,
                'code': user.office.code,
                'directorate': {
                    'id': user.office.directorate.id,
                    'name': user.office.directorate.name,
                } if getattr(user.office, 'directorate', None) else None,
            } if getattr(user, 'office', None) else None,
            'working_office': None,
            'department': getattr(get_employee_profile(user), 'department', None),
            'phoneNumber': getattr(get_employee_profile(user), 'phone', None) or getattr(get_employee_profile(user), 'mno', None),
            'designation': getattr(get_employee_profile(user), 'designation', None),
        }
        return data

    def get_full_name(self, user):
        """Combine first_name and last_name, fallback to name field"""
        if user.first_name or user.last_name:
            return f"{user.first_name} {user.last_name}".strip()
        profile = getattr(user, 'employee_profile', None)
        return getattr(profile, 'name', '') or ''



# ---------------------------------------------------------------------------
# New RBAC serializers
# ---------------------------------------------------------------------------

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name', 'group', 'description', 'is_active']


class DirectorateSerializer(serializers.ModelSerializer):
    office_count = serializers.SerializerMethodField()

    class Meta:
        model = Directorate
        # `code` was removed from the Directorate model (migration 0006); listing it
        # here made the serializer raise ImproperlyConfigured whenever a row existed.
        fields = ['id', 'name', 'description', 'office_count', 'created_at', 'updated_at']

    def get_office_count(self, obj):
        return obj.offices.count()


class OfficeSerializer(serializers.ModelSerializer):
    directorate = serializers.PrimaryKeyRelatedField(queryset=Directorate.objects.all(), required=False, allow_null=True)
    directorate_details = serializers.SerializerMethodField()
    directorate_name = serializers.SerializerMethodField()

    class Meta:
        model = Office
        fields = ['id', 'name', 'code', 'directorate', 'directorate_details', 'directorate_name', 'created_at', 'updated_at']

    def get_directorate_details(self, obj):
        if not obj.directorate:
            return None
        return {
            'id': obj.directorate.id,
            'name': obj.directorate.name,
            'description': obj.directorate.description,
        }

    def get_directorate_name(self, obj):
        return obj.directorate_name


class DepartmentSerializer(serializers.ModelSerializer):
    directorate = serializers.PrimaryKeyRelatedField(queryset=Directorate.objects.all(), required=False, allow_null=True)
    directorate_details = serializers.SerializerMethodField()
    office_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'name', 'code', 'directorate', 'directorate_details', 'description', 'office_count', 'created_at', 'updated_at']

    def get_directorate_details(self, obj):
        if not obj.directorate:
            return None
        return {
            'id': obj.directorate.id,
            'name': obj.directorate.name,
            'description': obj.directorate.description,
        }

    def get_office_count(self, obj):
        return obj.offices.count()


class WorkingOfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingOffice
        fields = ['id', 'name_of_office', 'directorate_id', 'ac_office_id', 'cc_office_id']


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    user_count  = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'is_active', 'permissions', 'user_count', 'created_at', 'updated_at']

    def get_permissions(self, obj):
        perms = Permission.objects.filter(
            role_permissions__role=obj,
            role_permissions__is_active=True,
        )
        return PermissionSerializer(perms, many=True).data

    def get_user_count(self, obj):
        return obj.users.count()


class PermissionAuditLogSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)
    user_name  = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = PermissionAuditLog
        fields = [
            'id', 'role', 'role_name', 'user', 'user_name',
            'action', 'permission', 'old_permissions', 'new_permissions',
            'details', 'timestamp', 'ip_address',
        ]

# ... keep existing code (UserSerializer, EmployeeByIdSerializer, RegisterSerializer, ForgotPasswordSerializer, ResetPasswordSerializer, EmployeeDetailSerializer, CreateUserFromEmployeeSerializer, EmployeeToUserPreviewSerializer)


class UserSerializer(serializers.ModelSerializer):
    _id         = serializers.CharField(source='employee_id')
    employeeId  = serializers.CharField(source='employee_id')
    name        = serializers.SerializerMethodField()
    phoneNumber = serializers.SerializerMethodField()
    isActive    = serializers.BooleanField(source='is_active', required=False)
    otpEnabled  = serializers.BooleanField(source='otp_enabled', default=False, required=False)
    user_role   = RoleSerializer(read_only=True, allow_null=True)
    office      = OfficeSerializer(read_only=True, allow_null=True)
    working_office = serializers.SerializerMethodField()
    position_details = serializers.SerializerMethodField()
    department  = serializers.SerializerMethodField()
    designation = serializers.SerializerMethodField()
    user_role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source='user_role',
        write_only=True,
        required=False,
        allow_null=True,
    )
    office_id = serializers.PrimaryKeyRelatedField(
        queryset=Office.objects.all(),
        source='office',
        write_only=True,
        required=False,
        allow_null=True,
    )
    user_role_details = serializers.SerializerMethodField()
    office_details = serializers.SerializerMethodField()
    working_office_details = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            '_id', 'employeeId', 'name', 'email', 'phoneNumber', 'department', 'designation',
            'isActive', 'otpEnabled', 'user_role', 'user_role_id', 'office', 'office_id',
            'working_office', 'position_details', 'last_login', 'is_staff', 'is_superuser',
            'user_role_details', 'office_details', 'working_office_details', 'permissions'
        ]
        extra_kwargs = {
            'employeeId': {'read_only': True},
            '_id': {'read_only': True},
        }

    def get_name(self, obj):
        """Combine first_name and last_name, fallback to name field"""
        if obj.first_name or obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        profile = get_employee_profile(obj)
        return getattr(profile, 'name', '') or ''

    def get_phoneNumber(self, obj):
        profile = get_employee_profile(obj)
        return getattr(profile, 'phone', None) or getattr(profile, 'mno', None)

    def get_department(self, obj):
        profile = get_employee_profile(obj)
        return getattr(profile, 'department', None)

    def get_designation(self, obj):
        profile = get_employee_profile(obj)
        return getattr(profile, 'designation', None)

    def get_user_role_details(self, obj):
        if hasattr(obj, 'user_role') and obj.user_role:
            return {'id': obj.user_role.id, 'name': obj.user_role.name}
        return None

    def get_office_details(self, obj):
        if hasattr(obj, 'office') and obj.office:
            return {
                'id': obj.office.id,
                'name': obj.office.name,
                'code': obj.office.code,
                'directorate': {
                    'id': obj.office.directorate.id,
                    'name': obj.office.directorate.name,
                } if getattr(obj.office, 'directorate', None) else None,
            }
        return None

    def _erp_work_office_map(self):
        """Cache the empno -> work_office map from the ERP master table once per
        serializer instance so a user list doesn't fire one query per row."""
        cache = getattr(self, '_erp_office_cache', None)
        if cache is None:
            cache = {
                empno: office
                for empno, office in ErpEmployeeRecord.objects
                    .exclude(work_office__isnull=True)
                    .exclude(work_office__exact='')
                    .values_list('empno', 'work_office')
                if empno
            }
            self._erp_office_cache = cache
        return cache

    def get_working_office(self, obj):
        # Prefer the linked Office FK (populated by sync_erp_employees). Fall back
        # to the raw ERP work_office for users not yet linked or without an ERP
        # record, so the value is never blank when the data exists somewhere.
        if obj.office_id and obj.office and obj.office.name:
            return obj.office.name
        return self._erp_work_office_map().get(obj.employee_id) or None

    def get_working_office_details(self, obj):
        return None

    def get_position_details(self, obj):
        profile = get_employee_profile(obj)
        position_name = getattr(profile, 'position', None)
        if position_name:
            return {'name': position_name}
        return None

    def get_permissions(self, obj):
        return obj.get_permission_codenames()

    def update(self, instance, validated_data):
        profile = get_employee_profile(instance)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Handle 'name' from request data (it's a SerializerMethodField so not in validated_data)
        request = self.context.get('request')
        profile_updates = []
        if request and 'name' in request.data:
            name_value = request.data['name']
            if name_value is not None:
                name_str = str(name_value).strip()
                logger.info(f"UserSerializer.update: Setting name to '{name_str}' for user {instance.employee_id}")
                parts = name_str.split(' ', 1)
                instance.first_name = parts[0]
                instance.last_name = parts[1] if len(parts) > 1 else ''
                if profile:
                    profile.name = name_str
                    profile_updates.append('name')

        if request:
            if 'phoneNumber' in request.data and profile:
                phone_value = request.data['phoneNumber']
                profile.phone = phone_value
                profile.mno = phone_value
                profile_updates.extend(['phone', 'mno'])
            if 'department' in request.data and profile:
                profile.department = request.data['department']
                profile_updates.append('department')
            if 'designation' in request.data and profile:
                profile.designation = request.data['designation']
                profile_updates.append('designation')

        logger.info(f"UserSerializer.update: Saving user {instance.employee_id} with validated_data: {validated_data}")
        instance.save()
        if profile and profile_updates:
            profile.save(update_fields=list(dict.fromkeys(profile_updates)))
        return instance


class EmployeeByIdSerializer(serializers.ModelSerializer):
    _id = serializers.CharField(source='employee_id')
    employeeId = serializers.CharField(source='employee_id')
    name = serializers.SerializerMethodField()
    isActive = serializers.BooleanField(source='is_active')
    otpEnabled = serializers.BooleanField(source='otp_enabled')
    department = serializers.SerializerMethodField()
    designation = serializers.SerializerMethodField()
    phoneNumber = serializers.SerializerMethodField()
    position_name = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            '_id', 'name', 'email', 'employeeId', 'department',
            'phoneNumber', 'designation', 'position_name', 'isActive', 'otpEnabled', 'permissions',
            'user_role', 'office'
        ]

    def get_name(self, obj):
        """Combine first_name and last_name, fallback to name field"""
        if obj.first_name or obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        profile = get_employee_profile(obj)
        return getattr(profile, 'name', '') or ''

    def get_department(self, obj):
        profile = get_employee_profile(obj)
        return getattr(profile, 'department', None)

    def get_designation(self, obj):
        profile = get_employee_profile(obj)
        return getattr(profile, 'designation', None)

    def get_phoneNumber(self, obj):
        profile = get_employee_profile(obj)
        return getattr(profile, 'phone', None) or getattr(profile, 'mno', None)

    def get_position_name(self, obj):
        profile = get_employee_profile(obj)
        return getattr(profile, 'position', None)

    def get_permissions(self, obj):
        return obj.get_permission_codenames()




class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), source='user_role', required=True)
    office = serializers.PrimaryKeyRelatedField(queryset=Office.objects.all(), required=False, allow_null=True)
    working_office = serializers.PrimaryKeyRelatedField(queryset=WorkingOffice.objects.all(), required=False, allow_null=True, write_only=True)
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    department = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    designation = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = CustomUser
        fields = ['employee_id', 'name', 'username', 'email', 'phone', 'department', 'designation', 'password', 'role', 'office', 'working_office']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        name = validated_data.pop('name', None)
        phone = validated_data.pop('phone', None)
        department = validated_data.pop('department', None)
        designation = validated_data.pop('designation', None)
        working_office = validated_data.pop('working_office', None)
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()

        employee_profile_defaults = {
            'name': name or '',
            'phone': phone or '',
            'mno': phone or '',
            'department': department or '',
            'designation': designation or '',
        }
        EmployeeDetail.objects.update_or_create(
            employee_id=user.employee_id,
            defaults={
                'user': user,
                'email': user.email,
                **employee_profile_defaults,
            },
        )
        return user

    def validate(self, data):
        if CustomUser.objects.filter(employee_id=data['employee_id']).exists():
            raise serializers.ValidationError("A user with this employee ID already exists.")
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    employee_id = serializers.CharField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)


class EmployeeDetailSerializer(serializers.ModelSerializer):
    user_employee_id = serializers.CharField(source='user.employee_id', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    has_user_account = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDetail
        fields = ['employee_id', 'user_employee_id', 'user_email', 'has_user_account', 'name', 'email', 'phone', 'position', 'level', 'service',
                  'group', 'qualification', 'seniority', 'retirement', 'mno', 'department', 'designation']

    def get_has_user_account(self, obj):
        return obj.user_id is not None


class EmployeeWriteSerializer(serializers.ModelSerializer):
    """Create/update serializer for EmployeeDetail (manual employee management).

    Employees are distinct from user accounts — `user` is intentionally not
    writable here. `employee_id` is the primary key: settable on create, locked
    on update. Email uniqueness is enforced by the model.
    """
    class Meta:
        model = EmployeeDetail
        fields = ['employee_id', 'name', 'email', 'phone', 'mno', 'position', 'level',
                  'service', 'group', 'qualification', 'seniority', 'retirement',
                  'department', 'designation']

    def validate_employee_id(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError("Employee ID is required.")
        # On create, the ID must be unique. On update it's read-only (see below),
        # so this only guards creation.
        if self.instance is None and EmployeeDetail.objects.filter(employee_id=value).exists():
            raise serializers.ValidationError("An employee with this Employee ID already exists.")
        return value

    def get_fields(self):
        fields = super().get_fields()
        # The primary key cannot change on update.
        if self.instance is not None:
            fields['employee_id'].read_only = True
        return fields


class CreateUserFromEmployeeSerializer(serializers.Serializer):
    employee_id = serializers.CharField(max_length=10)
    role_id = serializers.IntegerField()
    auto_generate_password = serializers.BooleanField(default=True)
    password = serializers.CharField(max_length=128, required=False, allow_blank=True)

    def validate_employee_id(self, value):
        """Validate that the employee exists and hasn't been converted to a user yet"""
        try:
            employee = EmployeeDetail.objects.get(employee_id=value)
        except EmployeeDetail.DoesNotExist:
            raise serializers.ValidationError(f"Employee with ID {value} does not exist.")

        # Check if user already exists for this employee
        if CustomUser.objects.filter(employee_id=value).exists():
            raise serializers.ValidationError(f"User already exists for employee ID {value}.")

        return value

    def validate_role_id(self, value):
        """Validate that the role exists"""
        try:
            role = Role.objects.get(id=value)
        except Role.DoesNotExist:
            raise serializers.ValidationError(f"Role with ID {value} does not exist.")
            raise serializers.ValidationError(f"Role with ID {value} does not exist.")
        return value

    def validate(self, data):
        """Cross-field validation"""
        if not data.get('auto_generate_password') and not data.get('password'):
            raise serializers.ValidationError("Password is required when auto_generate_password is False.")
        return data

    def create(self, validated_data):
        """Create a new user from employee data"""
        employee_id = validated_data['employee_id']
        role_id = validated_data['role_id']
        auto_generate_password = validated_data.get('auto_generate_password', True)
        custom_password = validated_data.get('password')

        # Get employee and role objects
        employee = EmployeeDetail.objects.get(employee_id=employee_id)
        role = Role.objects.get(id=role_id)

        # Generate password if needed
        if auto_generate_password:
            password = self._generate_random_password()
        else:
            password = custom_password

        # Credentials are derived from the employee record: when a phone number
        # exists, the user logs in via OTP to that number (no password to
        # distribute). Otherwise fall back to the auto-generated password.
        phone = employee.phone or employee.mno

        # Map employee fields to user fields
        user_data = {
            'employee_id': employee.employee_id,
            'email': employee.email,
            'user_role': role,
            'is_active': True,
            'otp_enabled': bool(phone),
            'password': password
        }

        # Create the user
        user = CustomUser.objects.create_user(**user_data)

        EmployeeDetail.objects.update_or_create(
            employee_id=employee.employee_id,
            defaults={
                'user': user,
                'email': employee.email,
                'name': employee.name or '',
                'phone': employee.phone or employee.mno or '',
                'mno': employee.mno or employee.phone or '',
                'department': employee.department or employee.group or '',
                'designation': employee.designation or employee.position or '',
                'position': employee.position or '',
                'service': employee.service or '',
                'group': employee.group or '',
                'qualification': employee.qualification or '',
                'seniority': employee.seniority,
                'retirement': employee.retirement,
            },
        )

        # Store the plain password for response (will be removed in production)
        user._generated_password = password if auto_generate_password else None

        return user

    def _generate_random_password(self, length=12):
        """Generate a random password"""
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(characters) for _ in range(length))


DEFAULT_SIGNUP_ROLE_NAME = 'Member'


def _validate_signup_employee(value):
    """Shared validation for self-signup: the employee must exist, have no
    account yet, and have a phone (for OTP) and a unique email (for the account).
    Returns the cleaned employee_id."""
    value = (value or '').strip()
    try:
        employee = EmployeeDetail.objects.get(employee_id=value)
    except EmployeeDetail.DoesNotExist:
        raise serializers.ValidationError("No employee record found for this Employee ID.")
    if CustomUser.objects.filter(employee_id=value).exists():
        raise serializers.ValidationError(
            "An account already exists for this Employee ID. Please log in or reset your password."
        )
    if not (employee.phone or employee.mno):
        raise serializers.ValidationError(
            "No phone number is on file for this employee. Please contact the administrator."
        )
    if not employee.email:
        raise serializers.ValidationError(
            "No email address is on file for this employee. Please contact the administrator."
        )
    if CustomUser.objects.filter(email=employee.email).exists():
        raise serializers.ValidationError(
            "An account using this employee's email already exists. Please log in "
            "with that account or contact the administrator."
        )
    return value


class SignupSerializer(serializers.Serializer):
    """
    Step 1 of self-service signup: validate the employee_id. The view then sends
    an OTP to the employee's registered phone. No account is created at this step.
    """
    employee_id = serializers.CharField(max_length=10)

    def validate_employee_id(self, value):
        return _validate_signup_employee(value)


class SignupVerifySerializer(serializers.Serializer):
    """
    Step 2 of self-service signup: verify the OTP and let the user set their own
    password. The account is created here (active, password chosen by the user,
    no forced first-login change).
    """
    employee_id = serializers.CharField(max_length=10)
    otp = serializers.CharField(min_length=4, max_length=8)
    password = serializers.CharField(min_length=8, max_length=128, write_only=True)

    DEFAULT_ROLE_NAME = DEFAULT_SIGNUP_ROLE_NAME

    def validate_employee_id(self, value):
        return _validate_signup_employee(value)

    def create(self, validated_data):
        employee_id = validated_data['employee_id']
        employee = EmployeeDetail.objects.get(employee_id=employee_id)
        role = Role.objects.filter(name=self.DEFAULT_ROLE_NAME).first()

        with transaction.atomic():
            user = CustomUser.objects.create_user(
                employee_id=employee.employee_id,
                email=employee.email,
                password=validated_data['password'],
                user_role=role,
                is_active=True,
                otp_enabled=False,
                must_change_password=False,
            )
            EmployeeDetail.objects.update_or_create(
                employee_id=employee.employee_id,
                defaults={
                    'user': user,
                    'email': employee.email,
                    'name': employee.name or '',
                    'phone': employee.phone or employee.mno or '',
                    'mno': employee.mno or employee.phone or '',
                    'department': employee.department or employee.group or '',
                    'designation': employee.designation or employee.position or '',
                    'position': employee.position or '',
                    'service': employee.service or '',
                    'group': employee.group or '',
                    'qualification': employee.qualification or '',
                    'seniority': employee.seniority,
                    'retirement': employee.retirement,
                },
            )
        return user


class EmployeeToUserPreviewSerializer(serializers.ModelSerializer):
    """Serializer to preview how employee data will map to user fields"""
    mapped_name = serializers.SerializerMethodField()
    mapped_phone = serializers.SerializerMethodField()
    mapped_department = serializers.SerializerMethodField()
    mapped_designation = serializers.SerializerMethodField()
    can_create_user = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDetail
        fields = ['employee_id', 'name', 'email', 'phone', 'position', 'level', 'service', 'group', 'mno', 'department', 'designation',
                  'mapped_name', 'mapped_phone', 'mapped_department', 'mapped_designation', 'can_create_user']

    def get_mapped_name(self, obj):
        return obj.name or ''

    def get_mapped_phone(self, obj):
        return obj.phone or obj.mno or ''

    def get_mapped_department(self, obj):
        return obj.department or obj.group or ''

    def get_mapped_designation(self, obj):
        return obj.designation or obj.position or ''

    def get_can_create_user(self, obj):
        return obj.user_id is None and not CustomUser.objects.filter(employee_id=obj.employee_id).exists()


class OTPVerifySerializer(serializers.Serializer):
    user_id = serializers.CharField(write_only=True)
    otp = serializers.CharField(write_only=True, min_length=4, max_length=8)


class OTPResendSerializer(serializers.Serializer):
    user_id = serializers.CharField()
