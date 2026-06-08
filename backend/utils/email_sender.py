# backend/utils/email_sender.py
import logging
import requests
from django.conf import settings
from .message_templates import get_committee_email_template # Added

logger = logging.getLogger(__name__)

def send_committee_email(receiver, name, role, committee_name, policy_number, project_name, file_path=None):
    """
    Sends an email notification to a committee member using the specified API.
    
    API Details:
    - URL: settings.EMAIL_API_URL (from .env)
    - Method: POST
    """
    if not receiver:
        logger.warning(f"No email address provided for user {name}. Skipping email.")
        return False

    api_url = getattr(settings, 'EMAIL_API_URL', '')
    if not api_url:
        logger.error("EMAIL_API_URL is not configured; skipping email.")
        return False
    
    subject = f"Committee Formation - {committee_name}"
    
    # Use standardized template
    content = get_committee_email_template(
        name=name,
        role=role,
        committee_name=committee_name,
        policy_number=policy_number,
        project_name=project_name
    )

    # Prepare payload
    payload = {
        "receiver": receiver,
        "subject": subject,
        "content": content,
        "ccAddress": "", # Add CC if needed
        "filePath": file_path or "",
        "hasAttachment": "Y" if file_path else "N"
    }

    try:
        logger.info(f"Sending Email to {receiver} with subject: {subject}")
        response = requests.post(api_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                logger.info(f"Email sent successfully to {receiver}. Response: {result.get('message')}")
                return True
            else:
                logger.error(f"Email API returned error status: {result}")
                return False
        else:
            logger.error(f"Email API returned HTTP error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.exception(f"Exception occurred while sending email to {receiver}: {str(e)}")
        return False
