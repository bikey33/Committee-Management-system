# backend/utils/ntc_otp.py
"""
NTC OTP Service integration.
Wraps the NTC OTP API for sending and validating OTPs.
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Configurable via settings / .env
NTC_OTP_BASE_URL = getattr(settings, 'NTC_OTP_BASE_URL', 'http://10.26.204.149:3000')
NTC_OTP_TIMEOUT = int(getattr(settings, 'NTC_OTP_TIMEOUT', 5))


def send_otp(phone_number: str, message: str = None) -> dict:
    """
    Send an OTP to the given phone number via the NTC OTP Service.

    Args:
        phone_number: Full phone number including country code (e.g. "97798xxxxxxxxx")
        message: Optional custom message. Must contain <OTP> placeholder.

    Returns:
        dict with keys: success (bool), seq_no (str or None), error (str or None)
    """
    url = f"{NTC_OTP_BASE_URL}/api/otp/send"
    payload = {"phone": phone_number}

    if message:
        payload["message"] = message

    try:
        response = requests.post(url, json=payload, timeout=NTC_OTP_TIMEOUT)
        data = response.json()

        if response.status_code == 200 and data.get("success"):
            inner = data.get("data", {})
            seq_no = inner.get("data", {}).get("seq_no") or inner.get("seq_no")
            if seq_no:
                logger.info(f"OTP sent successfully to {phone_number[-4:]}, seq_no: {seq_no}")
                return {"success": True, "seq_no": str(seq_no), "error": None}
            else:
                logger.error(f"OTP send response missing seq_no: {data}")
                return {"success": False, "seq_no": None, "error": "Missing seq_no in response"}
        else:
            error_msg = data.get("message", "Unknown error from NTC service")
            logger.error(f"OTP send failed: {error_msg}")
            return {"success": False, "seq_no": None, "error": error_msg}

    except requests.Timeout:
        logger.error(f"OTP send timed out for {phone_number[-4:]}")
        return {"success": False, "seq_no": None, "error": "NTC OTP service timed out"}
    except requests.ConnectionError:
        logger.error(f"Cannot connect to NTC OTP service at {NTC_OTP_BASE_URL}")
        return {"success": False, "seq_no": None, "error": "Cannot connect to NTC OTP service"}
    except Exception as e:
        logger.exception(f"Unexpected error sending OTP: {e}")
        return {"success": False, "seq_no": None, "error": str(e)}


def validate_otp(seq_no: str, otp_code: str) -> dict:
    """
    Validate an OTP using the NTC OTP Service.

    Args:
        seq_no: The sequence number returned from send_otp.
        otp_code: The OTP code entered by the user.

    Returns:
        dict with keys: success (bool), error (str or None)
    """
    url = f"{NTC_OTP_BASE_URL}/api/otp/validate"
    payload = {"seq_no": seq_no, "otp": otp_code}

    try:
        response = requests.post(url, json=payload, timeout=NTC_OTP_TIMEOUT)
        data = response.json()

        if response.status_code == 200 and data.get("success"):
            data_payload = data.get("data")
            code = None
            desc = None

            if isinstance(data_payload, dict):
                code = data_payload.get("code")
                desc = data_payload.get("description") or data_payload.get("desc")
            elif isinstance(data_payload, str):
                desc = data_payload

            # Some NTC responses return success=true with empty data payload.
            # Treat that as success (observed in live response).
            if code == 0 or (code is None and not desc):
                logger.info(f"OTP validated successfully for seq_no: {seq_no}")
                return {"success": True, "error": None}

            desc = desc or data.get("message") or "Validation failed"
            logger.warning(
                f"OTP validation failed for seq_no {seq_no}: code={code}, desc={desc}, response={data}"
            )
            return {"success": False, "error": desc}

        error_msg = data.get("message", "OTP validation failed")
        logger.warning(
            f"OTP validation request failed: status={response.status_code}, data={data}"
        )
        return {"success": False, "error": error_msg}

    except requests.Timeout:
        logger.error(f"OTP validate timed out for seq_no: {seq_no}")
        return {"success": False, "error": "NTC OTP service timed out"}
    except requests.ConnectionError:
        logger.error(f"Cannot connect to NTC OTP service at {NTC_OTP_BASE_URL}")
        return {"success": False, "error": "Cannot connect to NTC OTP service"}
    except Exception as e:
        logger.exception(f"Unexpected error validating OTP: {e}")
        return {"success": False, "error": str(e)}
