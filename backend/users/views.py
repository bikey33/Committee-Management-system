
# backend/users/views.py
import uuid
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser, EmployeeDetail, PermissionAuditLog, OTPLog, Role, Permission, RolePermission, Directorate, Office, Department, Position, WorkingOffice
from .serializers import (
    RegisterSerializer, UserSerializer, RoleSerializer, PermissionSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer, EmployeeByIdSerializer,
    CustomTokenObtainPairSerializer, EmployeeDetailSerializer, EmployeeWriteSerializer,
    CreateUserFromEmployeeSerializer, EmployeeToUserPreviewSerializer,
    OTPVerifySerializer, OTPResendSerializer, PermissionAuditLogSerializer,
    DirectorateSerializer, OfficeSerializer, DepartmentSerializer, PositionSerializer, WorkingOfficeSerializer,
    SignupSerializer, SignupVerifySerializer
)
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from .tasks import send_password_reset_email, send_welcome_email
from .utils import is_superadmin
from .permissions import IsSuperAdmin, HasPermission, OfficeAdminOrAbove
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from utils.ntc_otp import send_otp as ntc_send_otp, validate_otp as ntc_validate_otp
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()
logger = logging.getLogger(__name__)


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def resolve_user_phone(user):
    """Return a user's phone number from their EmployeeDetail, or None.

    CustomUser has no phone field — it lives on the linked EmployeeDetail
    (`phone`, falling back to `mno`). The reverse OneToOne raises
    ObjectDoesNotExist (not AttributeError) when no profile exists, so a plain
    getattr would not catch it.
    """
    try:
        profile = user.employee_profile
    except ObjectDoesNotExist:
        return None
    if not profile:
        return None
    return (profile.phone or profile.mno or '').strip() or None




class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @swagger_auto_schema(
        tags=["Auth"],
        operation_summary="Obtain JWT access and refresh tokens",
        operation_description="Provide employee_id (or email) and password to receive JWT tokens and user profile. If OTP is enabled, returns otp_required=true instead.",
        request_body=CustomTokenObtainPairSerializer,
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "refresh": openapi.Schema(type=openapi.TYPE_STRING),
                    "access": openapi.Schema(type=openapi.TYPE_STRING),
                    "user": openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "_id": openapi.Schema(type=openapi.TYPE_STRING),
                            "name": openapi.Schema(type=openapi.TYPE_STRING),
                            "email": openapi.Schema(type=openapi.TYPE_STRING),
                            "employeeId": openapi.Schema(type=openapi.TYPE_STRING),
                            "role": openapi.Schema(type=openapi.TYPE_OBJECT),
                            "department": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                            "phoneNumber": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                            "designation": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                            "isActive": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "otpEnabled": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            "permissions": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                        },
                    ),
                },
            ),
            400: "Invalid credentials or OTP required",
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as exc:
            # Check if this is an OTP-required response (not a real error)
            if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
                detail = exc.detail
                # Handle both direct dict and list-wrapped dict formats
                if isinstance(detail, list) and len(detail) > 0 and isinstance(detail[0], dict):
                    detail = detail[0]
                if detail.get('otp_required'):
                    return Response({
                        'otp_required': True,
                        'user_id': detail.get('user_id', [''])[0] if isinstance(detail.get('user_id'), list) else detail.get('user_id', ''),
                        'phone_hint': detail.get('phone_hint', [''])[0] if isinstance(detail.get('phone_hint'), list) else detail.get('phone_hint', ''),
                        'detail': 'OTP sent to your registered phone number.',
                    }, status=status.HTTP_200_OK)
            raise
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Auth"],
        operation_summary="Verify OTP and complete login",
        request_body=OTPVerifySerializer,
        responses={200: 'JWT tokens + user data', 400: 'Invalid OTP', 429: 'Too many attempts'}
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data['user_id']
        otp_code = str(serializer.validated_data['otp']).strip()

        max_attempts = int(getattr(settings, 'OTP_MAX_ATTEMPTS', 5))

        try:
            user = User.objects.get(employee_id=user_id)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Invalid user.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find the latest active OTP log
        otp_log = OTPLog.objects.filter(
            user=user,
            status='sent',
            expires_at__gt=timezone.now(),
        ).order_by('-created_at').first()

        if not otp_log:
            return Response(
                {'detail': 'No active OTP found. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check max attempts
        if otp_log.attempts >= max_attempts:
            otp_log.status = 'failed'
            otp_log.save(update_fields=['status'])
            return Response(
                {'detail': 'Maximum OTP attempts exceeded. Please request a new OTP.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Validate via NTC service (transactionId stored in seq_no, mobile in phone)
        logger.info(
            f"OTP verify attempt: user={user_id}, txn={otp_log.seq_no}, otp_length={len(str(otp_code))}"
        )
        result = ntc_validate_otp(otp_log.seq_no, otp_code, otp_log.phone)

        if result['success']:
            otp_log.status = 'verified'
            otp_log.verified_at = timezone.now()
            otp_log.save(update_fields=['status', 'verified_at'])

            # Update last_login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            # Issue JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    '_id': user._id,
                    'name': f"{user.first_name} {user.last_name}".strip() or user.name or '',
                    'email': user.email,
                    'employeeId': user.employee_id,
                    'user_role': {
                        'id': user.user_role.id,
                        'name': user.user_role.name,
                        'description': user.user_role.description,
                        'permissions': user.get_permission_codenames(),
                    } if getattr(user, 'user_role', None) else None,
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
                    'user_role_id': user.user_role.id if getattr(user, 'user_role', None) else None,
                    'department': getattr(getattr(user, 'employee_profile', None), 'department', None),
                    'phoneNumber': getattr(getattr(user, 'employee_profile', None), 'phone', None) or getattr(getattr(user, 'employee_profile', None), 'mno', None),
                    'designation': getattr(getattr(user, 'employee_profile', None), 'designation', None),
                    'isActive': user.is_active,
                    'otpEnabled': user.otp_enabled,
                    'permissions': user.get_permission_codenames(), # Use helper method instead of non-existent field
                },
            }, status=status.HTTP_200_OK)
        else:
            # Increment attempts
            otp_log.attempts += 1
            remaining = max_attempts - otp_log.attempts
            if otp_log.attempts >= max_attempts:
                otp_log.status = 'failed'
            otp_log.save(update_fields=['attempts', 'status'])

            return Response(
                {
                    'detail': result.get('error') or 'Invalid OTP. Please try again.',
                    'remaining_attempts': max(0, remaining),
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class OTPResendView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Auth"],
        operation_summary="Resend OTP",
        request_body=OTPResendSerializer,
        responses={200: 'OTP resent', 429: 'Rate limit exceeded'}
    )
    def post(self, request):
        serializer = OTPResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.validated_data['user_id']
        max_resends = int(getattr(settings, 'OTP_MAX_RESENDS', 3))
        expiry_minutes = int(getattr(settings, 'OTP_EXPIRY_MINUTES', 5))

        try:
            user = User.objects.get(employee_id=user_id)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Invalid user.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Rate limiting: count OTPs sent in last 10 minutes
        ten_minutes_ago = timezone.now() - timedelta(minutes=10)
        recent_count = OTPLog.objects.filter(
            user=user,
            purpose='login',
            created_at__gte=ten_minutes_ago,
        ).count()

        if recent_count >= max_resends:
            return Response(
                {'detail': 'Too many OTP requests. Please wait before trying again.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        phone_number = resolve_user_phone(user)
        if not phone_number:
            return Response(
                {'detail': 'No phone number registered.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Invalidate previous active OTPs
        OTPLog.objects.filter(user=user, status='sent').update(status='invalidated')

        # Send new OTP
        otp_result = ntc_send_otp(phone_number)

        if not otp_result['success']:
            return Response(
                {'detail': 'Failed to send OTP. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Get client IP
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip_address = forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')

        OTPLog.objects.create(
            user=user,
            phone=phone_number,
            seq_no=otp_result['transaction_id'],
            purpose='login',
            status='sent',
            ip_address=ip_address,
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
        )

        phone_hint = f"***{phone_number[-4:]}" if len(phone_number) >= 4 else "***"

        return Response({
            'detail': 'OTP resent successfully.',
            'phone_hint': phone_hint,
        }, status=status.HTTP_200_OK)


class RegisterView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="Register a new user (admin only)",
        operation_description="Creates a new user. Only SUPERADMIN can access.",
        request_body=RegisterSerializer,
        responses={
            201: openapi.Response(
                description="User registered successfully",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                                      "message": openapi.Schema(type=openapi.TYPE_STRING)})
            ),
            400: "Validation error",
            403: "Forbidden",
        },
    )
    def post(self, request):
        if not (is_superadmin(request.user) or request.user.has_rbac_permission('users.manage')):
            return Response(
                {"detail": "You do not have permission to register new users."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Temporarily disabled Celery/Redis for user creation
            # try:
            #     send_welcome_email.delay(user.email, user.employee_id, user.username or user.name)
            # except Exception as e:
            #     logger.error(f"Failed to queue welcome email for {user.employee_id}: {str(e)}")
                
            return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="Get current user profile",
        responses={200: UserSerializer},
    )
    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="Update current user profile (self-service)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "phoneNumber": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={200: UserSerializer, 400: "Validation error"},
    )
    def patch(self, request):
        user = request.user
        allowed_fields = {'name', 'phoneNumber', 'phone', 'otp_enabled', 'otpEnabled'}
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        if 'phoneNumber' in data:
            data['phone'] = data.pop('phoneNumber')
        if 'otpEnabled' in data:
            data['otp_enabled'] = data.pop('otpEnabled')
        update_fields = []
        profile_updates = []
        if 'name' in data:
            user.first_name = data['name'].split(' ', 1)[0]
            user.last_name = data['name'].split(' ', 1)[1] if len(data['name'].split(' ', 1)) > 1 else ''
            update_fields.append('first_name')
            update_fields.append('last_name')
            profile = getattr(user, 'employee_profile', None)
            if profile:
                profile.name = data['name']
                profile_updates.append('name')
        if 'phone' in data:
            profile = getattr(user, 'employee_profile', None)
            if profile:
                profile.phone = data['phone']
                profile.mno = data['phone']
                profile_updates.extend(['phone', 'mno'])
        if 'otp_enabled' in data:
            user.otp_enabled = data['otp_enabled']
            update_fields.append('otp_enabled')
        if update_fields:
            user.save(update_fields=update_fields)
        if profile_updates:
            profile.save(update_fields=list(dict.fromkeys(profile_updates)))
        serializer = UserSerializer(user)
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """Allow authenticated users to change their own password."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Password"],
        operation_summary="Change own password",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "current_password": openapi.Schema(type=openapi.TYPE_STRING),
                "new_password": openapi.Schema(type=openapi.TYPE_STRING),
                "confirm_password": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["current_password", "new_password", "confirm_password"],
        ),
        responses={200: "Password changed", 400: "Validation error"},
    )
    def post(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not all([current_password, new_password, confirm_password]):
            return Response(
                {'detail': 'All fields are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != confirm_password:
            return Response(
                {'detail': 'New passwords do not match.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 6:
            return Response(
                {'detail': 'Password must be at least 6 characters.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if not user.check_password(current_password):
            return Response(
                {'detail': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        # Clear any forced-change flag now that the user has set their own password.
        user.must_change_password = False
        user.save()
        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)


class AdminResetPasswordView(APIView):
    """Allow admins to reset any user's password."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Password"],
        operation_summary="Admin reset user password",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "new_password": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["new_password"],
        ),
        responses={200: "Password reset", 403: "Forbidden", 404: "Not found"},
    )
    def post(self, request, employee_id):
        if not (is_superadmin(request.user) or request.user.has_rbac_permission('users.manage')):
            return Response(
                {'detail': 'You do not have permission to reset passwords.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        new_password = request.data.get('new_password')
        if not new_password or len(new_password) < 6:
            return Response(
                {'detail': 'Password must be at least 6 characters.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.get(employee_id=employee_id)
            user.set_password(new_password)
            user.save()
            return Response(
                {'message': f'Password for {user.employee_id} has been reset.'},
                status=status.HTTP_200_OK,
            )
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)


class SignupView(APIView):
    """
    Public self-service signup. Accepts an employee_id; if it matches an employee
    in the directory with no account, provisions a CustomUser with a random
    password SMSed to the employee's phone and forces a change on first login.
    Rate limited per employee_id and per client IP to prevent SMS flooding.
    """
    permission_classes = [AllowAny]

    SIGNUP_WINDOW_SECONDS = 10 * 60   # 10 minutes
    # Strict per-employee cap stops flooding one person's phone. The per-IP cap
    # is looser because many employees may share one office NAT/IP.
    SIGNUP_MAX_PER_EMPLOYEE = 3
    SIGNUP_MAX_PER_IP = 20

    def _rate_limited(self, key, limit):
        count = cache.get(key, 0)
        if count >= limit:
            return True
        # Re-set with the window TTL each increment (sliding-ish window).
        cache.set(key, count + 1, self.SIGNUP_WINDOW_SECONDS)
        return False

    # Signup OTP session: seq_no cached per employee_id between request & verify.
    SIGNUP_OTP_TTL_SECONDS = 10 * 60  # 10 minutes

    @staticmethod
    def _signup_otp_cache_key(employee_id):
        return f"signup_otp:{employee_id}"

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="Self-service signup — request OTP (public)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"employee_id": openapi.Schema(type=openapi.TYPE_STRING)},
            required=["employee_id"],
        ),
        responses={200: "OTP sent", 400: "Validation error", 429: "Too many requests", 502: "OTP gateway error"},
    )
    def post(self, request):
        employee_id = str(request.data.get('employee_id', '')).strip()
        if not employee_id:
            return Response({"detail": "Employee ID is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Validate first so genuine errors (unknown ID, existing account, no phone,
        # email already in use) return their real message and do NOT consume the
        # rate-limit budget — only requests that will actually trigger an OTP count.
        serializer = SignupSerializer(data={'employee_id': employee_id})
        if not serializer.is_valid():
            errors = serializer.errors.get('employee_id') or serializer.errors
            detail = errors[0] if isinstance(errors, list) and errors else "Signup failed."
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        # Rate limit the OTP-sending path by employee_id and by client IP.
        ip = get_client_ip(request) or 'unknown'
        if (self._rate_limited(f"signup:{employee_id}", self.SIGNUP_MAX_PER_EMPLOYEE)
                or self._rate_limited(f"signup_ip:{ip}", self.SIGNUP_MAX_PER_IP)):
            return Response(
                {"detail": "Too many signup requests. Please wait a few minutes and try again."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        employee = EmployeeDetail.objects.get(employee_id=employee_id)
        phone = employee.phone or employee.mno

        otp_result = ntc_send_otp(phone)
        if not otp_result.get('success'):
            logger.error(f"Signup OTP send failed for {employee_id}: {otp_result.get('error')}")
            return Response(
                {"detail": "Failed to send the verification code. Please try again later."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Remember the transactionId so the verify step can validate the entered OTP.
        cache.set(self._signup_otp_cache_key(employee_id), otp_result['transaction_id'],
                  self.SIGNUP_OTP_TTL_SECONDS)

        phone_hint = f"***{phone[-4:]}" if len(phone) >= 4 else "***"
        return Response({
            "status": "success",
            "detail": "A verification code has been sent to your registered phone number.",
            "employee_id": employee_id,
            "phone_hint": phone_hint,
        }, status=status.HTTP_200_OK)


class SignupVerifyView(APIView):
    """
    Public signup step 2: verify the OTP sent to the employee's phone and create
    the account with the password the user chooses.
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="Self-service signup — verify OTP & set password (public)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "employee_id": openapi.Schema(type=openapi.TYPE_STRING),
                "otp": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["employee_id", "otp", "password"],
        ),
        responses={201: "Account created", 400: "Invalid OTP / validation error"},
    )
    def post(self, request):
        serializer = SignupVerifySerializer(data=request.data)
        if not serializer.is_valid():
            # Surface the first field error in a friendly shape.
            first = next(iter(serializer.errors.values()))
            detail = first[0] if isinstance(first, list) and first else "Signup verification failed."
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        employee_id = serializer.validated_data['employee_id']
        otp = serializer.validated_data['otp']

        cache_key = SignupView._signup_otp_cache_key(employee_id)
        transaction_id = cache.get(cache_key)
        if not transaction_id:
            return Response(
                {"detail": "Your verification code has expired. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify against the same mobile number the OTP was sent to.
        employee = EmployeeDetail.objects.get(employee_id=employee_id)
        phone = employee.phone or employee.mno
        result = ntc_validate_otp(transaction_id, otp, phone)
        if not result.get('success'):
            return Response(
                {"detail": result.get('error') or "Invalid verification code. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            serializer.save()
        except Exception as e:
            logger.error(f"Signup verify failed for {employee_id}: {e}", exc_info=True)
            return Response({"detail": "Could not create your account. Please try again later."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # OTP consumed — clear the session so the code can't be reused.
        cache.delete(cache_key)

        return Response({
            "status": "success",
            "detail": "Your account has been created. You can now log in with your password.",
        }, status=status.HTTP_201_CREATED)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="Get current user profile (alias)",
        responses={200: UserSerializer},
    )
    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        data = dict(serializer.data)
        # Surface the forced-password-change flag so a page refresh still enforces it.
        data['mustChangePassword'] = request.user.must_change_password
        return Response(data)


class EffectivePermissionsView(APIView):
    """Return the current user's effective permissions including inherited ones and module access."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Get role info
        role_name = ''
        role_id = None
        effective_permissions = user.get_permission_codenames()
        
        if user.user_role:
            role_name = user.user_role.name
            role_id = user.user_role.id
        
        # Get module access configuration
        from .models import ModuleAccess
        module_access = list(
            ModuleAccess.objects.values('module', 'permissions', 'restricted_to')
        )
        
        return Response({
            'name': role_name,
            'role_name': role_name,
            'role_id': role_id,
            'effective_permissions': effective_permissions,
            'module_access': module_access,
        })

class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, HasPermission('users.view')]

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="List users (scoped by office)",
        responses={200: openapi.Response(description="List of users", schema=openapi.Schema(
            type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)))},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        logger.info(f"UserListView: User {user.employee_id} requesting user list")
        logger.info(f"UserListView: User role: {user.user_role.name if getattr(user, 'user_role', None) else 'No role'}")

        queryset = CustomUser.objects.all().order_by('-date_joined')
        
        from .utils import get_queryset_for_user
        queryset = get_queryset_for_user(user, queryset)
        
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(email__icontains=search) |
                Q(department__icontains=search)
            )
            
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        logger.info(f"UserListView: Returning {queryset.count()} users")
        return queryset

    def list(self, request, *args, **kwargs):
        logger.info(f"UserListView: GET request from user {request.user.employee_id}")

        try:
            queryset = self.get_queryset()
            
            page_size = int(request.query_params.get('page_size', 10))
            page = int(request.query_params.get('page', 1))
            
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            
            serializer = self.get_serializer(page_obj.object_list, many=True)
            
            return Response({
                'count': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': page,
                'page_size': page_size,
                'next': page_obj.next_page_number() if page_obj.has_next() else None,
                'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
                'results': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"UserListView: Error fetching users: {str(e)}", exc_info=True)
            return Response(
                {"detail": "Internal server error while fetching users"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmployeeByIdView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Employees"],
        operation_summary="Get user by employee ID",
        manual_parameters=[
            openapi.Parameter("employee_id", openapi.IN_PATH, description="Employee ID", type=openapi.TYPE_STRING),
        ],
        responses={200: EmployeeByIdSerializer, 404: "Not found"},
    )
    def get(self, request, employee_id):
        logger.debug(f"EmployeeByIdView called for employee_id: {employee_id}")
        try:
            user = CustomUser.objects.get(employee_id__iexact=employee_id)
            serializer = EmployeeByIdSerializer(user)
            return Response(
                {"status": "success", "data": {"user": serializer.data}},
                status=status.HTTP_200_OK
            )
        except CustomUser.DoesNotExist:
            logger.error(f"Employee not found for ID: {employee_id}")
            return Response(
                {"status": "error", "message": f"Employee not found for ID: {employee_id}"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return Response(
                {"status": "error", "message": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="Get user details (admin only)",
        manual_parameters=[openapi.Parameter("employee_id", openapi.IN_PATH,
                                             description="Employee ID", type=openapi.TYPE_STRING)],
        responses={200: UserSerializer, 404: "Not found", 403: "Forbidden"},
    )
    def get(self, request, employee_id):
        if not (is_superadmin(request.user) or request.user.has_rbac_permission('users.view') or request.user.has_rbac_permission('users.manage')):
            return Response(
                {'detail': 'You do not have permission to view user details.'},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            user = CustomUser.objects.get(employee_id=employee_id)
            serializer = UserSerializer(user, context={'request': request})
            return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="Update user (admin only)",
        request_body=UserSerializer,
        responses={200: UserSerializer, 400: "Validation error", 403: "Forbidden", 404: "Not found"},
    )
    def patch(self, request, employee_id):
        if not (is_superadmin(request.user) or request.user.has_rbac_permission('users.manage')):
            return Response(
                {'detail': 'You do not have permission to update users.'},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            user = CustomUser.objects.get(employee_id=employee_id)
            logger.info(f"UserDetailView.patch: Received data for user {employee_id}: {request.data}")
            serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                logger.info(f"UserDetailView.patch: Serializer is valid for user {employee_id}")
                serializer.save()
                return Response({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)
            logger.warning(f"UserDetailView.patch: Serializer errors for user {employee_id}: {serializer.errors}")
            return Response({"status": "error", "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="Delete user (admin only)",
        responses={204: "Deleted", 403: "Forbidden", 404: "Not found"},
    )
    def delete(self, request, employee_id):
        if not (is_superadmin(request.user) or request.user.has_rbac_permission('users.manage')):
            logger.warning(f"Delete denied: User {request.user.employee_id} attempted to delete {employee_id} without permission")
            return Response(
                {'detail': 'You do not have permission to delete users.'},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            user_to_delete = CustomUser.objects.get(employee_id=employee_id)
            
            # Additional safety: Don't allow deleting self
            if user_to_delete.employee_id == request.user.employee_id:
                return Response(
                    {'detail': 'You cannot delete your own account.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            logger.info(f"User {request.user.employee_id} is deleting user {employee_id}")
            user_to_delete.delete()
            return Response({"status": "success", "message": "User deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except CustomUser.DoesNotExist:
            logger.error(f"Delete failed: User {employee_id} not found")
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error during user deletion: {str(e)}", exc_info=True)
            return Response(
                {'detail': f"Failed to delete user: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RoleListView(generics.ListAPIView):
    """GET /roles/ — list all active roles (authenticated users)."""
    permission_classes = [IsAuthenticated]
    serializer_class = RoleSerializer

    def get_queryset(self):
        return Role.objects.filter(is_active=True)

    @swagger_auto_schema(tags=["Roles"], operation_summary="List all roles")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AvailablePermissionsView(APIView):
    """GET /permissions/ — list all 49 permission codenames from DB."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(tags=["Permissions"], operation_summary="List all permissions")
    def get(self, request):
        permissions = Permission.objects.filter(is_active=True).order_by('group', 'name')
        return Response(PermissionSerializer(permissions, many=True).data, status=status.HTTP_200_OK)


class PermissionAuditLogListView(generics.ListAPIView):
    """GET /permissions/audit/ — list permission audit logs (Super Admin only)."""
    serializer_class = PermissionAuditLogSerializer
    permission_classes = [IsAuthenticated, HasPermission('roles.manage')]

    @swagger_auto_schema(
        tags=["Permissions"],
        operation_summary="List permission audit logs (Super Admin only)",
        responses={200: openapi.Response(description="List of audit logs", schema=openapi.Schema(
            type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)))},
    )
    def get_queryset(self):
        queryset = PermissionAuditLog.objects.all()
        role_id = self.request.query_params.get('role_id')
        if role_id:
            queryset = queryset.filter(role_id=role_id)
        return queryset


class RoleCreateView(APIView):
    """POST /roles/ — create a new role (Super Admin only)."""
    permission_classes = [IsAuthenticated, HasPermission('roles.manage')]

    @swagger_auto_schema(
        tags=["Roles"],
        operation_summary="Create role (Super Admin only)",
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
            "name":        openapi.Schema(type=openapi.TYPE_STRING),
            "description": openapi.Schema(type=openapi.TYPE_STRING),
        }, required=["name"]),
        responses={201: RoleSerializer, 403: "Forbidden", 400: "Validation error"},
    )
    def post(self, request):
        name = request.data.get('name', '').strip()
        if not name:
            return Response({'error': 'Role name is required'}, status=status.HTTP_400_BAD_REQUEST)
        if Role.objects.filter(name__iexact=name).exists():
            return Response({'error': f'Role "{name}" already exists'}, status=status.HTTP_400_BAD_REQUEST)
        description = request.data.get('description', '')
        role = Role.objects.create(name=name, description=description)
        logger.info(f"Role '{role.name}' created by {request.user.employee_id}")
        return Response({'message': 'Role created', 'data': RoleSerializer(role).data}, status=status.HTTP_201_CREATED)


class RoleUpdateView(APIView):
    """PATCH /roles/<role_id>/ — update role name/description (Super Admin only)."""
    permission_classes = [IsAuthenticated, HasPermission('roles.manage')]

    @swagger_auto_schema(tags=["Roles"], operation_summary="Update role (Super Admin only)")
    def patch(self, request, role_id):
        try:
            role = Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
        if 'name' in request.data:
            role.name = request.data['name'].strip()
        if 'description' in request.data:
            role.description = request.data['description']
        if 'is_active' in request.data:
            role.is_active = bool(request.data['is_active'])
        role.save()
        return Response({'message': 'Role updated', 'data': RoleSerializer(role).data})


class RoleDeleteView(APIView):
    """DELETE /roles/<role_id>/ — delete role if no users assigned (Super Admin only)."""
    permission_classes = [IsSuperAdmin]

    @swagger_auto_schema(tags=["Roles"], operation_summary="Delete role (Super Admin only)")
    def delete(self, request, role_id):
        try:
            role = Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
        user_count = role.users.count()
        if user_count > 0:
            return Response(
                {'error': f'Cannot delete: {user_count} user(s) assigned. Reassign them first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        role.delete()
        return Response({'message': f'Role "{role.name}" deleted'}, status=status.HTTP_204_NO_CONTENT)


class RolePermissionsView(APIView):
    """
    GET  /roles/<role_id>/permissions/ — active permissions for a role.
    PUT  /roles/<role_id>/permissions/ — replace permission set (Super Admin only).
    """
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsSuperAdmin()]

    def get(self, request, role_id):
        try:
            role = Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
        perms = Permission.objects.filter(role_permissions__role=role, role_permissions__is_active=True)
        return Response(PermissionSerializer(perms, many=True).data)

    def put(self, request, role_id):
        try:
            role = Role.objects.get(pk=role_id)
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
        codenames = request.data.get('permissions', [])
        if not isinstance(codenames, list):
            return Response({'error': '"permissions" must be a list of codenames'}, status=status.HTTP_400_BAD_REQUEST)
        valid = set(Permission.objects.filter(codename__in=codenames).values_list('codename', flat=True))
        invalid = set(codenames) - valid
        if invalid:
            return Response({'error': f'Unknown codenames: {list(invalid)}'}, status=status.HTTP_400_BAD_REQUEST)
        RolePermission.objects.filter(role=role).update(is_active=False)
        for codename in codenames:
            perm = Permission.objects.get(codename=codename)
            rp, _ = RolePermission.objects.get_or_create(role=role, permission=perm, defaults={'granted_by': request.user})
            rp.is_active = True
            rp.save(update_fields=['is_active'])
        logger.info(f"Role '{role.name}' permissions updated by {request.user.employee_id}")
        return Response({'message': 'Permissions updated', 'data': RoleSerializer(role).data})





class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            employee_id = serializer.validated_data['employee_id']
            try:
                user = CustomUser.objects.get(employee_id=employee_id)
            except CustomUser.DoesNotExist:
                return Response({'detail': 'User with this Employee ID does not exist.'}, status=status.HTTP_404_NOT_FOUND)

            phone_number = resolve_user_phone(user)
            if not phone_number:
                return Response({'detail': 'No phone number registered for this user. Please contact admin.'}, status=status.HTTP_400_BAD_REQUEST)

            # Send OTP via NTC service
            otp_result = ntc_send_otp(phone_number)

            if not otp_result['success']:
                logger.error(f"Failed to send password reset OTP to {user.employee_id}: {otp_result['error']}")
                return Response({'detail': 'Failed to send OTP. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Invalidate previous active OTPs for password_reset
            OTPLog.objects.filter(user=user, status='sent', purpose='password_reset').update(status='invalidated')

            # Create OTP log
            expiry_minutes = int(getattr(settings, 'OTP_EXPIRY_MINUTES', 5))
            OTPLog.objects.create(
                user=user,
                phone=phone_number,
                seq_no=otp_result['transaction_id'],
                purpose='password_reset',
                status='sent',
                ip_address=get_client_ip(request),
                expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
            )

            phone_hint = f"***{phone_number[-4:]}" if len(phone_number) >= 4 else "***"

            return Response({
                'message': 'OTP sent to your registered phone number.',
                'user_id': user.employee_id,
                'phone_hint': phone_hint,
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OTPPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.data.get('user_id')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not all([user_id, otp, new_password, confirm_password]):
            return Response({'detail': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({'detail': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 6:
            return Response({'detail': 'Password must be at least 6 characters.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(employee_id=user_id)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Find latest active password_reset OTP (either sent or already verified)
        otp_log = OTPLog.objects.filter(
            user=user,
            purpose='password_reset',
            status__in=['sent', 'verified'],
            expires_at__gt=timezone.now(),
        ).order_by('-created_at').first()

        if not otp_log:
            return Response({'detail': 'No active OTP found. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

        # Only validate against NTC if status is 'sent'
        # If it's already 'verified', we assume the previous step (OTPVerifyView) handled it.
        if otp_log.status == 'sent':
            # Validate OTP via NTC (transactionId in seq_no, mobile in phone)
            validate_result = ntc_validate_otp(otp_log.seq_no, otp, otp_log.phone)

            if not validate_result['success']:
                otp_log.attempts = getattr(otp_log, 'attempts', 0) + 1
                otp_log.save()
                error_msg = validate_result.get('error', 'Invalid OTP. Please try again.')
                return Response({'detail': error_msg}, status=status.HTTP_400_BAD_REQUEST)

            # OTP valid - mark as verified
            otp_log.status = 'verified'
            otp_log.verified_at = timezone.now()
            otp_log.save()
        
        # If status was already 'verified', we proceed to reset.

        user.set_password(new_password)
        user.save()

        logger.info(f"Password reset successful for user {user.employee_id} via OTP")
        return Response({'message': 'Password reset successful. You can now login with your new password.'}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Password"],
        operation_summary="Reset password",
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
            "token": openapi.Schema(type=openapi.TYPE_STRING),
            "uid": openapi.Schema(type=openapi.TYPE_STRING),
            "new_password": openapi.Schema(type=openapi.TYPE_STRING),
            "confirm_password": openapi.Schema(type=openapi.TYPE_STRING),
        }, required=["token", "uid", "new_password", "confirm_password"]),
        responses={200: openapi.Response(description="Password reset successful", schema=openapi.Schema(
            type=openapi.TYPE_OBJECT, properties={"message": openapi.Schema(type=openapi.TYPE_STRING)})), 400: "Invalid token or input"},
    )
    def post(self, request):
        # Get parameters from both body and query params to support both methods
        data = request.data.copy()
        if not data.get('token'):
            data['token'] = request.GET.get('token')
        if not data.get('uid'):
            data['uid'] = request.GET.get('uid')

        token = data.get('token')
        uid = data.get('uid')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if not all([token, uid, new_password, confirm_password]):
            return Response({
                'message': 'Token, UID, new password, and confirm password are required.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({
                'message': 'Passwords do not match.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Find user by reset token
            user = CustomUser.objects.filter(reset_token=token).first()
            if not user:
                return Response({
                    'message': 'Invalid or expired reset token.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Reset password and clear token
            user.set_password(new_password)
            user.reset_token = None
            user.save()

            return Response({
                'message': 'Password reset successful.'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'message': 'Failed to reset password. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmployeeDetailListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmployeeDetailSerializer

    @swagger_auto_schema(
        tags=["Employees"],
        operation_summary="List employee details",
        responses={200: openapi.Response(description="List of employees", schema=openapi.Schema(
            type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)))},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = EmployeeDetail.objects.all().order_by('employee_id')
        
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(employee_id__icontains=search) |
                Q(email__icontains=search) |
                Q(position__icontains=search) |
                Q(group__icontains=search)
            )
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        page_size = int(request.query_params.get('page_size', 10))
        page = int(request.query_params.get('page', 1))
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        serializer = self.get_serializer(page_obj.object_list, many=True)
        
        return Response({
            'count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page,
            'page_size': page_size,
            'next': page_obj.next_page_number() if page_obj.has_next() else None,
            'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class EmployeeCreateView(generics.CreateAPIView):
    """POST /employee-details/create/ — manually create an employee record."""
    permission_classes = [IsAuthenticated]
    serializer_class = EmployeeWriteSerializer

    def create(self, request, *args, **kwargs):
        if not (is_superadmin(request.user) or request.user.has_rbac_permission('users.manage')):
            return Response(
                {"detail": "You do not have permission to create employees."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)


class EmployeeUpdateView(generics.UpdateAPIView):
    """PATCH/PUT /employee-details/<employee_id>/ — update an employee record."""
    permission_classes = [IsAuthenticated]
    serializer_class = EmployeeWriteSerializer
    queryset = EmployeeDetail.objects.all()
    lookup_field = 'employee_id'

    def update(self, request, *args, **kwargs):
        if not (is_superadmin(request.user) or request.user.has_rbac_permission('users.manage')):
            return Response(
                {"detail": "You do not have permission to update employees."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Default to partial updates so the frontend can send only changed fields.
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


class ValidateEmployeeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Employees"],
        operation_summary="Validate employee details",
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
            "employee_id": openapi.Schema(type=openapi.TYPE_STRING),
            "email": openapi.Schema(type=openapi.TYPE_STRING),
        }, required=["employee_id", "email"]),
        responses={200: openapi.Response(description="Valid/invalid", schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                                         "valid": openapi.Schema(type=openapi.TYPE_BOOLEAN)})), 404: "Not found", 400: "Bad request"},
    )
    def post(self, request):
        employee_id = request.data.get('employee_id')
        email = request.data.get('email')
        if not employee_id or not email:
            return Response(
                {'detail': 'employee_id and email are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            EmployeeDetail.objects.get(employee_id=employee_id, email=email)
            return Response({'valid': True}, status=status.HTTP_200_OK)
        except EmployeeDetail.DoesNotExist:
            return Response(
                {'detail': 'No matching EmployeeDetail found'},
                status=status.HTTP_404_NOT_FOUND
            )


class CreateUserFromEmployeeView(APIView):
    """Create a new user from existing employee data"""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="Create user from employee (admin only)",
        request_body=CreateUserFromEmployeeSerializer,
        responses={201: openapi.Response(description="User created", schema=openapi.Schema(
            type=openapi.TYPE_OBJECT)), 400: "Validation error", 403: "Forbidden"},
    )
    def post(self, request):
        if not (is_superadmin(request.user) or request.user.has_rbac_permission('users.manage')):
            return Response(
                {"detail": "You do not have permission to create users from employees."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CreateUserFromEmployeeSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                response_data = UserSerializer(user).data

                # Temporarily disabled Celery/Redis for user creation
                # try:
                #     send_welcome_email.delay(user.email, user.employee_id, user.name or user.username)
                # except Exception as e:
                #     logger.error(f"Failed to queue welcome email for {user.employee_id}: {str(e)}")

                # Include generated password in response if auto-generated
                if hasattr(user, '_generated_password') and user._generated_password:
                    response_data['generated_password'] = user._generated_password

                return Response({
                    "status": "success",
                    "message": "User created successfully from employee data",
                    "data": response_data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Error creating user from employee: {str(e)}", exc_info=True)
                return Response({
                    "status": "error",
                    "message": "Failed to create user from employee data",
                    "detail": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "status": "error",
            "message": "Validation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class EmployeeToUserPreviewView(APIView):
    """Preview how employee data will be mapped to user fields"""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Employees"],
        operation_summary="Preview employee-to-user mapping",
        manual_parameters=[openapi.Parameter("employee_id", openapi.IN_PATH,
                                             description="Employee ID", type=openapi.TYPE_STRING)],
        responses={200: EmployeeToUserPreviewSerializer, 403: "Forbidden", 404: "Not found"},
    )
    def get(self, request, employee_id):
        if not (is_superadmin(request.user) or request.user.has_rbac_permission('users.view')):
            return Response(
                {"detail": "You do not have permission to access this endpoint."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            employee = EmployeeDetail.objects.get(employee_id=employee_id)
            serializer = EmployeeToUserPreviewSerializer(employee)
            return Response({
                "status": "success",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        except EmployeeDetail.DoesNotExist:
            return Response({
                "status": "error",
                "message": f"Employee with ID {employee_id} not found"
            }, status=status.HTTP_404_NOT_FOUND)


class AvailableEmployeesForUserCreationView(APIView):
    """Get list of employees that can be converted to users"""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Employees"],
        operation_summary="List employees available for user creation",
        manual_parameters=[openapi.Parameter("search", openapi.IN_QUERY,
                                             description="Search query", type=openapi.TYPE_STRING, required=False)],
        responses={200: openapi.Response(description="List of employees", schema=openapi.Schema(
            type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)))},
    )
    def get(self, request):
        if not (is_superadmin(request.user) or request.user.has_rbac_permission('users.view')):
            return Response(
                {"detail": "You do not have permission to access this endpoint."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get employees that don't have corresponding users
        existing_user_employee_ids = CustomUser.objects.values_list('employee_id', flat=True)
        available_employees = EmployeeDetail.objects.exclude(employee_id__in=existing_user_employee_ids)

        # Apply search filter if provided
        search = request.query_params.get('search', '')
        if search:
            available_employees = available_employees.filter(
                # Assuming EmployeeDetail has name, employee_id, email, group, position fields
                # models.Q(name__icontains=search) |
                # models.Q(employee_id__icontains=search) |
                # models.Q(email__icontains=search) |
                # models.Q(group__icontains=search) |
                # models.Q(position__icontains=search)
            )

        serializer = EmployeeToUserPreviewSerializer(available_employees, many=True)
        return Response({
            "status": "success",
            "count": available_employees.count(),
            "data": serializer.data
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Office hierarchy endpoints
# ---------------------------------------------------------------------------

class DirectorateListView(generics.ListAPIView):
    """GET /directorates/ — list all directorates."""
    permission_classes = [IsAuthenticated]
    serializer_class = DirectorateSerializer

    def get_queryset(self):
        return Directorate.objects.all().prefetch_related('departments', 'offices')


class DirectorateCreateView(generics.CreateAPIView):
    """POST /directorates/create/ — create a new directorate."""
    permission_classes = [IsAuthenticated, HasPermission('settings.offices')]
    serializer_class = DirectorateSerializer


class DirectorateUpdateView(generics.UpdateAPIView):
    """PATCH /directorates/<id>/ — edit a directorate."""
    permission_classes = [IsAuthenticated, HasPermission('settings.offices')]
    serializer_class = DirectorateSerializer
    queryset = Directorate.objects.all()


class DirectorateDeleteView(generics.DestroyAPIView):
    """DELETE /directorates/<id>/delete/ — delete a directorate."""
    permission_classes = [IsAuthenticated, HasPermission('settings.offices')]
    queryset = Directorate.objects.all()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.offices.exists():
            return Response({'error': 'Cannot delete directorate with related offices.'}, status=status.HTTP_400_BAD_REQUEST)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

class OfficeListView(generics.ListAPIView):
    """GET /offices/ — list all offices."""
    permission_classes = [IsAuthenticated]
    serializer_class = OfficeSerializer

    def get_queryset(self):
        queryset = Office.objects.select_related('directorate').all()
        directorate_id = self.request.query_params.get('directorate')
        if directorate_id:
            queryset = queryset.filter(directorate_id=directorate_id)
        return queryset

class OfficeCreateView(generics.CreateAPIView):
    """POST /offices/create/ — create a new office."""
    permission_classes = [IsAuthenticated, HasPermission('settings.offices')]
    serializer_class = OfficeSerializer

class OfficeUpdateView(generics.UpdateAPIView):
    """PATCH /offices/<id>/ — edit an office."""
    permission_classes = [IsAuthenticated, HasPermission('settings.offices')]
    serializer_class = OfficeSerializer
    queryset = Office.objects.all()

class OfficeDeleteView(generics.DestroyAPIView):
    """DELETE /offices/<id>/delete/ — delete an office."""
    permission_classes = [IsAuthenticated, HasPermission('settings.offices')]
    queryset = Office.objects.all()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if CustomUser.objects.filter(office=instance).exists():
            return Response({'error': 'Cannot delete office with assigned users.'}, status=status.HTTP_400_BAD_REQUEST)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

# ---------------------------------------------------------------------------
# Position list endpoint
# ---------------------------------------------------------------------------

class PositionListView(generics.ListAPIView):
    """GET /positions/ — list all positions."""
    permission_classes = [IsAuthenticated]
    serializer_class = PositionSerializer
    queryset = Position.objects.all().order_by('-level', 'name')


class WorkingOfficeListView(generics.ListAPIView):
    """GET /working-offices/ — list all working offices."""
    permission_classes = [IsAuthenticated]
    serializer_class = WorkingOfficeSerializer
    queryset = WorkingOffice.objects.all()
