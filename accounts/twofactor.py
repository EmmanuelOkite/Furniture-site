"""
Optional two-factor authentication with an authenticator app (TOTP, RFC 6238).

Everything 2FA-specific lives here. The login view only calls `is_enabled()`
and `verify()`, so another method could be added without changing the login flow.
"""

import hmac
import re
import secrets
import time

import pyotp
import segno
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import BackupCode, TOTPDevice
from .security import keyed_hash

TIME_STEP = 30
ALLOWED_DRIFT_STEPS = 1  # accept the previous and next 30-second code too
BACKUP_CODE_COUNT = 10


def is_enabled(user):
    return TOTPDevice.objects.filter(user=user).exists()


def new_secret():
    return pyotp.random_base32()


def provisioning_uri(user, secret):
    return pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=settings.ACCOUNTS_TOTP_ISSUER)


def qr_code_data_uri(uri):
    return segno.make(uri, error="m").svg_data_uri(scale=5, border=2)


def _clean_code(code):
    return re.sub(r"[\s-]", "", code or "").lower()


def match_totp(secret, code, last_used_step=None):
    """The time step the 6-digit code belongs to, or None. Steps already used are refused."""
    code = _clean_code(code)
    if not re.fullmatch(r"\d{6}", code):
        return None
    totp = pyotp.TOTP(secret)
    current = int(time.time()) // TIME_STEP
    for step in range(current - ALLOWED_DRIFT_STEPS, current + ALLOWED_DRIFT_STEPS + 1):
        if last_used_step is not None and step <= last_used_step:
            continue
        if hmac.compare_digest(totp.generate_otp(step), code):
            return step
    return None


def _hash_backup_code(code):
    return keyed_hash(_clean_code(code), "backup-code")


def _format_backup_code(raw):
    return f"{raw[:5]}-{raw[5:]}"


@transaction.atomic
def generate_backup_codes(user):
    """Replace the user's backup codes. The plain codes are returned once and never stored."""
    BackupCode.objects.filter(user=user).delete()
    codes = [_format_backup_code(secrets.token_hex(5)) for _ in range(BACKUP_CODE_COUNT)]
    BackupCode.objects.bulk_create(BackupCode(user=user, code_hash=_hash_backup_code(c)) for c in codes)
    return codes


def remaining_backup_codes(user):
    return BackupCode.objects.filter(user=user, used_at__isnull=True).count()


@transaction.atomic
def enable(user, secret):
    TOTPDevice.objects.update_or_create(user=user, defaults={"secret": secret, "last_used_step": None})
    return generate_backup_codes(user)


@transaction.atomic
def disable(user):
    TOTPDevice.objects.filter(user=user).delete()
    BackupCode.objects.filter(user=user).delete()


def verify(user, code):
    """
    Check an authenticator code or a backup code.
    Returns "totp", "backup" or None. Each code can be used only once.
    """
    with transaction.atomic():
        device = TOTPDevice.objects.select_for_update().filter(user=user).first()
        if device is None:
            return None
        step = match_totp(device.secret, code, device.last_used_step)
        if step is not None:
            device.last_used_step = step
            device.save(update_fields=["last_used_step"])
            return "totp"
    used = BackupCode.objects.filter(
        user=user, code_hash=_hash_backup_code(code), used_at__isnull=True
    ).update(used_at=timezone.now())
    return "backup" if used == 1 else None
