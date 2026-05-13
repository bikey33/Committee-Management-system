# backend/users/authentication.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class CustomAuthBackend(ModelBackend):
    def authenticate(self, request, employee_id=None, password=None, **kwargs):
        logger.debug(f"Authenticating with employee_id: {employee_id}")
        if employee_id is None:
            logger.error("No employee_id provided for authentication")
            return None

        try:
            # Try employee_id (case-insensitive)
            user = User.objects.get(employee_id__iexact=employee_id)
            logger.debug(f"Found user by employee_id: {user.employee_id}")
        except User.DoesNotExist:
            try:
                # Try email
                user = User.objects.get(email=employee_id)
                logger.debug(f"Found user by email: {user.email}")
            except User.DoesNotExist:
                logger.error(f"No user found for identifier: {employee_id}")
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            logger.debug(f"Authentication successful for user: {user.employee_id}")
            return user
        logger.error(f"Password check failed for user: {user.employee_id}")
        return None

    def user_can_authenticate(self, user):
        is_active = getattr(user, 'is_active', False)
        logger.debug(f"Checking if user can authenticate: {user.employee_id}, is_active: {is_active}")
        return is_active

