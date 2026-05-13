# backend/committee/tasks.py
import logging
from celery import shared_task
from utils.sms_sender import send_committee_sms
from utils.email_sender import send_committee_email

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_committee_notification_task(self, phone_number, name, role, policy_number, project_name, committee_type, email=None, committee_name=None, file_path=None):
    """
    Asynchronous task to send both SMS and Email notifications to a committee member.
    """
    logger.info(f"Starting notification task for {name} ({phone_number})")
    
    # 1. Send SMS
    try:
        sms_success = send_committee_sms(
            phone_number=phone_number,
            name=name,
            role=role,
            policy_number=policy_number,
            project_name=project_name,
            committee_type=committee_type
        )
        if not sms_success:
            logger.warning(f"SMS sending failed for {name}")
    except Exception as e:
        logger.error(f"Error in SMS task for {name}: {str(e)}")

    # 2. Send Email if provided
    if email:
        try:
            email_success = send_committee_email(
                receiver=email,
                name=name,
                role=role,
                committee_name=committee_name or project_name,
                policy_number=policy_number,
                project_name=project_name,
                file_path=file_path
            )
            if not email_success:
                logger.warning(f"Email sending failed for {name} ({email})")
        except Exception as e:
            logger.error(f"Error in Email task for {name}: {str(e)}")
            
    return f"Notifications processed for {name}"
