# backend/users/permissions.py
"""
DRF permission classes for the new RBAC system.
"""
from rest_framework.permissions import BasePermission

def _get_role_name(user):
    try:
        return user.user_role.name.upper() if user.user_role_id else None
    except Exception:
        return None

class IsSuperAdmin(BasePermission):
    message = "Only Super Admin can perform this action."
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return getattr(request.user, 'is_superuser', False) or request.user.is_super_admin()

class OfficeAdminOrAbove(BasePermission):
    message = "Office Admin or above is required."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

def HasPermission(codename: str):
    class _HasPermission(BasePermission):
        message = f"Permission '{codename}' is required."
        def has_permission(self, request, view):
            if not (request.user and request.user.is_authenticated):
                return False
            if getattr(request.user, 'is_superuser', False) or request.user.is_super_admin():
                return True
            return request.user.has_rbac_permission(codename)
    _HasPermission.__name__ = f'HasPermission_{codename.replace(".", "_")}'
    _HasPermission.__qualname__ = _HasPermission.__name__
    return _HasPermission

class CanManageUser(BasePermission):
    message = "You do not have permission to manage this user."
    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated)