# backend/utils/ntc_otp.py
"""
NTC OTP Service integration.

Wraps the NTC OTP module:
  - Send:   POST {base}/otpmodule/sendotp    {"mobileNumber": "98...", "systemId": "2"}
            -> returns a transactionId
  - Verify: POST {base}/otpmodule/verifyotp  {"mobileNumber": "98...", "transactionId": "...", "otp": "..."}

Base URL / timeout come from settings (NTC_OTP_BASE_URL, NTC_OTP_TIMEOUT); the
systemId reuses SMS_SYSTEM_ID. Read at call time so .env changes take effect.
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _base_url() -> str:
    return getattr(settings, "NTC_OTP_BASE_URL", "http://10.26.192.122:8083")


def _timeout() -> int:
    return int(getattr(settings, "NTC_OTP_TIMEOUT", 10))


def _system_id() -> str:
    return str(getattr(settings, "SMS_SYSTEM_ID", "2"))


def _normalize_mobile(phone_number: str) -> str:
    """Reduce to the 10-digit mobile number the OTP module expects (e.g. 9851117226)."""
    digits = "".join(filter(str.isdigit, str(phone_number or "")))
    if len(digits) > 10:
        digits = digits[-10:]
    return digits


def _extract_transaction_id(data):
    if not isinstance(data, dict):
        return None
    for key in ("transactionId", "transaction_id", "txnId", "transactionID", "transId"):
        if data.get(key):
            return data[key]
    inner = data.get("data")
    if isinstance(inner, dict):
        return _extract_transaction_id(inner)
    return None


def _is_verify_success(data) -> bool:
    """Best-effort interpretation of the verifyotp response. Raw response is logged
    by the caller path so the parsing can be tightened if the shape differs."""
    if not isinstance(data, dict):
        return str(data).strip().lower() in ("success", "verified", "valid", "true")
    for key in ("success", "valid", "verified"):
        if key in data:
            return bool(data[key])
    status = str(data.get("status", "")).lower()
    if status in ("success", "ok", "verified", "valid", "true"):
        return True
    code = data.get("responseCode", data.get("code"))
    if code is not None and str(code) in ("0", "200"):
        return True
    msg = str(data.get("message") or data.get("description") or data.get("desc") or "").lower()
    if any(w in msg for w in ("success", "verified", "valid")):
        return True
    inner = data.get("data")
    if isinstance(inner, dict):
        return _is_verify_success(inner)
    return False


def send_otp(phone_number: str) -> dict:
    """
    Request an OTP for a mobile number.

    Returns dict: {success: bool, transaction_id: str|None, error: str|None}
    """
    mobile = _normalize_mobile(phone_number)
    url = f"{_base_url()}/otpmodule/sendotp"
    payload = {"mobileNumber": mobile, "systemId": _system_id()}

    try:
        response = requests.post(url, json=payload, timeout=_timeout())
        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code == 200:
            txn = _extract_transaction_id(data)
            if txn:
                logger.info(f"OTP sent to ...{mobile[-4:]}, transactionId: {txn}")
                return {"success": True, "transaction_id": str(txn), "error": None}
            logger.error(f"OTP send: no transactionId in response: {data}")
            return {
                "success": False,
                "transaction_id": None,
                "error": data.get("message") or data.get("description") or "No transaction id in OTP response",
            }

        logger.error(f"OTP send HTTP {response.status_code}: {response.text[:300]}")
        return {
            "success": False,
            "transaction_id": None,
            "error": f"OTP service returned HTTP {response.status_code}",
        }

    except requests.Timeout:
        logger.error(f"OTP send timed out for ...{mobile[-4:]}")
        return {"success": False, "transaction_id": None, "error": "NTC OTP service timed out"}
    except requests.ConnectionError:
        logger.error(f"Cannot connect to NTC OTP service at {_base_url()}")
        return {"success": False, "transaction_id": None, "error": "Cannot connect to NTC OTP service"}
    except Exception as e:
        logger.exception(f"Unexpected error sending OTP: {e}")
        return {"success": False, "transaction_id": None, "error": str(e)}


def validate_otp(transaction_id: str, otp_code: str, phone_number: str) -> dict:
    """
    Validate an OTP for a mobile number + transaction.

    Returns dict: {success: bool, error: str|None}
    """
    mobile = _normalize_mobile(phone_number)
    url = f"{_base_url()}/otpmodule/verifyotp"
    payload = {"mobileNumber": mobile, "transactionId": transaction_id, "otp": str(otp_code)}

    try:
        response = requests.post(url, json=payload, timeout=_timeout())
        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code == 200 and _is_verify_success(data):
            logger.info(f"OTP validated for transactionId: {transaction_id}")
            return {"success": True, "error": None}

        msg = (
            data.get("message") or data.get("description") or data.get("desc")
            or "Invalid or expired OTP"
        ) if isinstance(data, dict) else "Invalid or expired OTP"
        logger.warning(
            f"OTP validation failed (txn {transaction_id}): status={response.status_code}, data={data}"
        )
        return {"success": False, "error": msg}

    except requests.Timeout:
        logger.error(f"OTP validate timed out for txn: {transaction_id}")
        return {"success": False, "error": "NTC OTP service timed out"}
    except requests.ConnectionError:
        logger.error(f"Cannot connect to NTC OTP service at {_base_url()}")
        return {"success": False, "error": "Cannot connect to NTC OTP service"}
    except Exception as e:
        logger.exception(f"Unexpected error validating OTP: {e}")
        return {"success": False, "error": str(e)}
