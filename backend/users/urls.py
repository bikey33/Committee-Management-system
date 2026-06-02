# backend/users/urls.py
from django.urls import path
from .views import (
    RegisterView, UserListView, UserProfileView, MeView,
    RoleListView, RoleCreateView, RoleUpdateView, RoleDeleteView, RolePermissionsView,
    ForgotPasswordView, ResetPasswordView, OTPPasswordResetView, UserDetailView, EmployeeByIdView, EmployeeDetailListView,
    ValidateEmployeeDetailView, CustomTokenObtainPairView,
    CreateUserFromEmployeeView, EmployeeToUserPreviewView, AvailableEmployeesForUserCreationView,
    OTPVerifyView, OTPResendView, AvailablePermissionsView, PermissionAuditLogListView,
    EffectivePermissionsView, ChangePasswordView, AdminResetPasswordView,
    DirectorateListView, DirectorateCreateView, DirectorateUpdateView, DirectorateDeleteView,
    OfficeListView, OfficeCreateView, OfficeUpdateView, OfficeDeleteView,
    PositionListView, WorkingOfficeListView,
)

urlpatterns = [
    path('positions/', PositionListView.as_view(), name='position-list'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('otp-verify/', OTPVerifyView.as_view(), name='otp-verify'),
    path('otp-resend/', OTPResendView.as_view(), name='otp-resend'),
    path('register/', RegisterView.as_view(), name='register'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('otp-reset-password/', OTPPasswordResetView.as_view(), name='otp-reset-password'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    # Move this UP so it is checked before the general <str:employee_id> matcher.
    path('users/create-from-employee/', CreateUserFromEmployeeView.as_view(), name='create-user-from-employee'),
    
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<str:employee_id>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<str:employee_id>/admin-reset-password/', AdminResetPasswordView.as_view(), name='admin-reset-password'),
    path('employee/<str:employee_id>/', EmployeeByIdView.as_view(), name='employee-by-id'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('me/', MeView.as_view(), name='me'),
    path('me/permissions/', EffectivePermissionsView.as_view(), name='me-permissions'),
    path('roles/', RoleListView.as_view(), name='role-list'),
    path('roles/create/', RoleCreateView.as_view(), name='role-create'),
    path('roles/<int:role_id>/', RoleUpdateView.as_view(), name='role-update'),
    path('roles/<int:role_id>/delete/', RoleDeleteView.as_view(), name='role-delete'),
    path('roles/<int:role_id>/permissions/', RolePermissionsView.as_view(), name='role-permissions'),
    path('permissions/', AvailablePermissionsView.as_view(), name='permissions-available'),
    path('permissions/audit/', PermissionAuditLogListView.as_view(), name='permissions-audit'),
    path('employee-details/', EmployeeDetailListView.as_view(), name='employee-detail-list'),
    path('validate-employee/', ValidateEmployeeDetailView.as_view(), name='validate-employee'),
    
    path('employees/preview-user/<str:employee_id>/', EmployeeToUserPreviewView.as_view(), name='employee-to-user-preview'),
    path('employees/available-for-users/', AvailableEmployeesForUserCreationView.as_view(), name='available-employees-for-users'),
    path('directorates/', DirectorateListView.as_view(), name='directorate-list'),
    path('directorates/create/', DirectorateCreateView.as_view(), name='directorate-create'),
    path('directorates/<int:pk>/', DirectorateUpdateView.as_view(), name='directorate-update'),
    path('directorates/<int:pk>/delete/', DirectorateDeleteView.as_view(), name='directorate-delete'),
    path('offices/', OfficeListView.as_view(), name='office-list'),
    path('offices/create/', OfficeCreateView.as_view(), name='office-create'),
    path('offices/<int:pk>/', OfficeUpdateView.as_view(), name='office-update'),
    path('offices/<int:pk>/delete/', OfficeDeleteView.as_view(), name='office-delete'),
    path('working-offices/', WorkingOfficeListView.as_view(), name='working-office-list'),
]
