# backend/utils/sms_sender.py
import logging
import requests
import urllib.parse
from django.conf import settings
from .message_templates import get_committee_sms_template # Added

logger = logging.getLogger(__name__)

def send_committee_sms(phone_number, name, role, policy_number, project_name, committee_type="Committee"):
    """
    Sends an SMS notification to a committee member using the NTC SMS API.
    """
    if not phone_number:
        logger.warning(f"No phone number provided for user {name}. Skipping SMS.")
        return False

    # Normalize phone number to 10 digits if needed (e.g. 9851117226)
    phone_str = str(phone_number)
    clean_phone = ''.join(filter(str.isdigit, phone_str))
    if len(clean_phone) > 10:
        clean_phone = clean_phone[-10:]

    # Use standardized template
    message = get_committee_sms_template(
        name=name,
        role=role,
        committee_type=committee_type,
        policy_number=policy_number,
        project_name=project_name
    )

    # Encode message for URL
    encoded_message = urllib.parse.quote(message)

    # API Parameters from user
    username = "NtcSmsSender"
    password = ">xfhT4:/W^6YyY,M" # Original password (unescaped for the URL builder)
    # Note: The user provided it as %3ExfhT4:/W^6YyY,M in the URL.
    # %3E is '>'
    
    # Construct URL
    # Using the exact password string provided in the example URL (already encoded where needed)
    base_url = "http://10.26.204.149:8080/updatedsmssender-1.0-SNAPSHOT/updatedsmssender/"
    url = (
        f"{base_url}?username={username}&password=%3ExfhT4:/W^6YyY,M"
        f"&cellNo={clean_phone}&message={encoded_message}&encoding=E"
    )

    try:
        logger.info(f"Sending SMS to {clean_phone}: {message}")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"SMS sent successfully to {clean_phone}. Response: {response.text}")
            return True
        else:
            logger.error(f"SMS API returned error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.exception(f"Exception occurred while sending SMS to {clean_phone}: {str(e)}")
        return False
