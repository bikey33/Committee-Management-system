# backend/utils/sms_sender.py
import logging
import requests
from django.conf import settings
from .message_templates import get_committee_sms_template # Added

logger = logging.getLogger(__name__)


def _send_via_console(clean_phone, message):
    """Dev backend: print the SMS to the server terminal instead of sending it.

    Used when settings.SMS_BACKEND == 'console' (the default in DEBUG), where the
    internal NTC SMS gateway is unreachable.
    """
    banner = "=" * 64
    print(
        f"\n{banner}\n"
        f"[SMS — console backend] (no real SMS sent)\n"
        f"To:      {clean_phone}\n"
        f"Message: {message}\n"
        f"{banner}\n",
        flush=True,
    )
    logger.info(f"[SMS console backend] To {clean_phone}: {message}")
    return True


def _send_via_gateway(clean_phone, message):
    """Production backend: deliver the SMS via the NTC SMS HTTP API.

    All connection details are read from settings (sourced from .env):
    SMS_API_URL, SMS_USERNAME, SMS_PASSWORD, SMS_SYSTEM_ID. The query params are
    passed via `requests`, which percent-encodes each value (the gateway decodes
    them — e.g. the password's '>' is sent as %3E).
    """
    base_url = getattr(settings, 'SMS_API_URL', '')
    params = {
        'username': getattr(settings, 'SMS_USERNAME', ''),
        'password': getattr(settings, 'SMS_PASSWORD', ''),
        'cellNo': clean_phone,
        'message': message,
        'encoding': 'E',
        'systemId': getattr(settings, 'SMS_SYSTEM_ID', ''),
    }

    try:
        logger.info(f"Sending SMS to {clean_phone}: {message}")
        response = requests.get(base_url, params=params, timeout=10)
        if response.status_code == 200:
            logger.info(f"SMS sent successfully to {clean_phone}. Response: {response.text}")
            return True
        logger.error(f"SMS API returned error {response.status_code}: {response.text}")
        return False
    except Exception as e:
        logger.exception(f"Exception occurred while sending SMS to {clean_phone}: {str(e)}")
        return False


def send_plain_sms(phone_number, message):
    """
    Send an arbitrary text message to a phone number.

    Delivery is routed by settings.SMS_BACKEND ('console' prints to the terminal,
    'gateway' calls the NTC SMS API). Returns True on success, False otherwise.
    Used for any non-templated SMS (e.g. delivering a signup password).
    """
    if not phone_number:
        logger.warning("No phone number provided. Skipping SMS.")
        return False

    # Normalize phone number to 10 digits if needed (e.g. 9851117226)
    clean_phone = ''.join(filter(str.isdigit, str(phone_number)))
    if len(clean_phone) > 10:
        clean_phone = clean_phone[-10:]

    backend = getattr(settings, 'SMS_BACKEND', 'gateway')
    if backend == 'console':
        return _send_via_console(clean_phone, message)
    return _send_via_gateway(clean_phone, message)


def send_committee_sms(phone_number, name, role, policy_number, project_name, committee_type="Committee"):
    """
    Sends an SMS notification to a committee member using the NTC SMS API.
    """
    if not phone_number:
        logger.warning(f"No phone number provided for user {name}. Skipping SMS.")
        return False

    # Use standardized template
    message = get_committee_sms_template(
        name=name,
        role=role,
        committee_type=committee_type,
        policy_number=policy_number,
        project_name=project_name
    )

    return send_plain_sms(phone_number, message)
