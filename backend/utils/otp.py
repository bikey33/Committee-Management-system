import random
import string
from typing import Optional

from django.core.cache import cache


OTP_CACHE_KEY_PREFIX = "otp:code:user:"
OTP_ATTEMPTS_KEY_PREFIX = "otp:attempts:user:"

# Defaults: 6-digit OTP, valid for 5 minutes, max 5 attempts
DEFAULT_OTP_LENGTH = 6
DEFAULT_OTP_TTL_SECONDS = 5 * 60
DEFAULT_MAX_ATTEMPTS = 5


def _cache_key_for_code(user_id: str) -> str:
    return f"{OTP_CACHE_KEY_PREFIX}{user_id}"


def _cache_key_for_attempts(user_id: str) -> str:
    return f"{OTP_ATTEMPTS_KEY_PREFIX}{user_id}"


def _generate_numeric_code(length: int) -> str:
    digits = string.digits
    return "".join(random.choice(digits) for _ in range(length))


def generate_otp(
    user_id: str,
    length: int = DEFAULT_OTP_LENGTH,
    ttl_seconds: int = DEFAULT_OTP_TTL_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> str:
    """
    Generate an OTP for the given user and store it in cache with TTL.

    Returns the plaintext OTP so the caller can deliver it (e.g., via SMS).
    """
    code = _generate_numeric_code(max(4, length))

    # Store OTP and reset attempts
    cache.set(_cache_key_for_code(user_id), code, timeout=ttl_seconds)
    cache.set(_cache_key_for_attempts(user_id), max_attempts, timeout=ttl_seconds)

    return code


def verify_otp(user_id: str, otp_input: Optional[str]) -> bool:
    """
    Verify the provided OTP for the user. Decrements remaining attempts on failure.
    Returns True on success, False otherwise.
    """
    if not otp_input:
        return False

    key_code = _cache_key_for_code(user_id)
    key_attempts = _cache_key_for_attempts(user_id)

    stored_code = cache.get(key_code)
    if stored_code is None:
        return False

    if str(otp_input) == str(stored_code):
        # Success: clear both keys
        cache.delete(key_code)
        cache.delete(key_attempts)
        return True

    # Failed attempt: decrement attempts and possibly clear
    remaining = cache.get(key_attempts)
    if remaining is None:
        remaining = DEFAULT_MAX_ATTEMPTS

    try:
        remaining = int(remaining) - 1
    except Exception:
        remaining = 0

    if remaining <= 0:
        cache.delete(key_code)
        cache.delete(key_attempts)
    else:
        # Preserve original expiry by resetting with same TTL is complex; acceptable to set a short TTL
        cache.set(key_attempts, remaining, timeout=DEFAULT_OTP_TTL_SECONDS)

    return False


