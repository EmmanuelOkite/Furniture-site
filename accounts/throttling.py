"""
Database-backed rate limiting and sign-in lockout.

The database is shared by every gunicorn worker and survives restarts, unlike
the in-process cache, and the project has no Redis. Keys are HMACs, so raw
emails and IP addresses are never stored here.
"""

from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import LoginLockout, RateLimit
from .security import get_client_ip, keyed_hash
from .validators import normalize_email_address


def _window_start(now, window_seconds):
    epoch = int(now.timestamp())
    return datetime.fromtimestamp(epoch - epoch % window_seconds, tz=dt_timezone.utc)


def hit(scope, identifier):
    """Count one request for `identifier` in `scope`; return True while under the limit."""
    limit, window = settings.ACCOUNTS_RATE_LIMITS[scope]
    key = keyed_hash(identifier or "unknown", f"ratelimit.{scope}")
    entry, created = RateLimit.objects.get_or_create(
        scope=scope,
        key=key,
        window_start=_window_start(timezone.now(), window),
        defaults={"count": 1},
    )
    if not created:
        RateLimit.objects.filter(pk=entry.pk).update(count=F("count") + 1)
        entry.refresh_from_db(fields=["count"])
    return entry.count <= limit


def allow(request, action, identifier=None):
    """
    Apply the per-IP limit for `action` and, if given, the per-identifier limit
    (e.g. per email). Both counters are always incremented.
    """
    allowed = hit(f"{action}:ip", get_client_ip(request))
    if identifier is not None:
        allowed = hit(f"{action}:id", identifier) and allowed
    return allowed


# --- Sign-in lockout with progressive delays --------------------------------


def _lockout_key(email):
    return keyed_hash(normalize_email_address(email), "login-lockout")


def lockout_remaining(email):
    """Seconds until sign-in for this email is allowed again (0 if not locked)."""
    entry = LoginLockout.objects.filter(key=_lockout_key(email)).only("locked_until").first()
    if entry is None or entry.locked_until is None:
        return 0
    return max(0, int((entry.locked_until - timezone.now()).total_seconds()))


def register_failure(email):
    """
    Record a failed sign-in. After ACCOUNTS_LOCKOUT_THRESHOLD failures the email
    is locked for ACCOUNTS_LOCKOUT_BASE_SECONDS, doubling with each further
    failure up to ACCOUNTS_LOCKOUT_MAX_SECONDS. Returns the lock length (0 if not locked).
    """
    now = timezone.now()
    with transaction.atomic():
        entry, _ = LoginLockout.objects.select_for_update().get_or_create(key=_lockout_key(email))
        reset_after = timedelta(seconds=settings.ACCOUNTS_LOCKOUT_RESET_SECONDS)
        if entry.last_failure_at and now - entry.last_failure_at > reset_after:
            entry.failure_count = 0
        entry.failure_count += 1
        entry.last_failure_at = now
        over = entry.failure_count - settings.ACCOUNTS_LOCKOUT_THRESHOLD
        seconds = 0
        if over >= 0:
            seconds = min(
                settings.ACCOUNTS_LOCKOUT_BASE_SECONDS * 2 ** min(over, 20),
                settings.ACCOUNTS_LOCKOUT_MAX_SECONDS,
            )
            entry.locked_until = now + timedelta(seconds=seconds)
        entry.save()
    return seconds


def clear_failures(email):
    LoginLockout.objects.filter(key=_lockout_key(email)).delete()
