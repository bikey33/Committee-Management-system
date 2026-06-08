import logging

from celery import shared_task
from django.core.mail import send_mail
from django.core.management import call_command
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_sms_task(self, phone_number, message):
    """
    Deliver a plain SMS asynchronously.

    Routing (console vs real gateway) is handled by send_plain_sms via
    settings.SMS_BACKEND. On a transient gateway failure the task retries a few
    times; once retries are exhausted it logs and gives up rather than raising,
    so callers (e.g. signup) are never blocked on SMS delivery.
    """
    from utils.sms_sender import send_plain_sms

    if send_plain_sms(phone_number, message):
        return f"SMS sent to {phone_number}"

    try:
        raise self.retry(exc=RuntimeError("SMS delivery failed"))
    except self.MaxRetriesExceededError:
        logger.error(f"SMS permanently failed for {phone_number} after retries")
        return f"SMS failed for {phone_number}"


@shared_task
def sync_erp_employees_task():
    """
    Periodically refresh the EmployeeDetail directory from the ERP staging table.

    Thin wrapper around the `sync_erp_employees` management command so the
    idempotent upsert logic lives in one place. Scheduled via CELERY_BEAT_SCHEDULE.
    """
    call_command('sync_erp_employees')
    return "ERP employee sync completed"


@shared_task
def send_password_reset_email(email, reset_token, employee_id, origin=None):
    """
    Send password reset email asynchronously using Celery.
    
    Args:
        email (str): User's email address
        reset_token (str): Generated reset token
        employee_id (str): User's employee ID
        origin (str): The origin URL from the request (e.g., https://pms.ntc.net.np)
    """
    try:
        # Use the provided origin or fall back to a default
        if not origin:
            origin = "https://pms.ntc.net.np"  # Production default
        
        # Remove trailing slash if present
        origin = origin.rstrip('/')
        
        # Create the reset link
        reset_link = f"{origin}/reset-password?token={reset_token}&uid={employee_id}"
        
        # Email subject and message
        subject = 'Password Reset Request'
        message = f'''
        Dear User,

        You have requested to reset your password. Please click the link below to reset your password:

        {reset_link}

        If you did not request this password reset, please ignore this email.

        This link will expire in 1 hour.

        Best regards,
        PMS Team
        '''
        
        # Send the email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
        return f"Password reset email sent successfully to {email}"
        
    except Exception as e:
        # Log the error and re-raise to mark task as failed
        print(f"Failed to send password reset email to {email}: {str(e)}")
        raise e


@shared_task
def send_welcome_email(email, employee_id, username):
    """
    Send welcome email to newly registered users.
    
    Args:
        email (str): User's email address
        employee_id (str): User's employee ID
        username (str): User's username
    """
    try:
        subject = 'Welcome to PMS - Account Created Successfully'
        message = f'''
        Dear {username},

        Welcome to the Procurement Management System (PMS)!

        Your account has been created successfully with the following details:
        - Employee ID: {employee_id}
        - Username: {username}
        - Email: {email}

        You can now log in to the system using your credentials.

        If you have any questions or need assistance, please contact the system administrator.

        Best regards,
        PMS Team
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
        return f"Welcome email sent successfully to {email}"
        
    except Exception as e:
        print(f"Failed to send welcome email to {email}: {str(e)}")
        raise e 