"""Sign-in logic, kept out of the views so it can be tested directly."""

import enum
import time
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.utils import timezone

from . import sessions, throttling, twofactor
from .emails import send_account_email
from .models import SecurityEvent
from .security import get_client_ip, record_event
from .validators import normalize_email_address

PENDING_2FA_SESSION_KEY = "_accounts_pending_2fa"


class LoginStatus(enum.Enum):
    OK = "ok"
    INVALID = "invalid"
    LOCKED = "locked"
    TWO_FACTOR_REQUIRED = "two_factor_required"


@dataclass
class LoginResult:
    status: LoginStatus
    user: object = None
    retry_after: int = 0
    extra: dict = field(default_factory=dict)


def check_credentials(request, email, password):
    """
    First sign-in step. Throttled per IP and locked per email (registered or not),
    and every failure gives the same answer whether or not the email exists.
    """
    email = normalize_email_address(email)

    if not throttling.allow(request, "login"):
        return LoginResult(LoginStatus.LOCKED, retry_after=settings.ACCOUNTS_RATE_LIMITS["login:ip"][1])

    remaining = throttling.lockout_remaining(email)
    if remaining:
        # Don't even check the password while locked.
        return LoginResult(LoginStatus.LOCKED, retry_after=remaining)

    user = authenticate(request, email=email, password=password)
    if user is None:
        lock_seconds = throttling.register_failure(email)
        known = _known_user(email)
        record_event(SecurityEvent.Type.LOGIN_FAILED, request, user=known)
        if lock_seconds:
            record_event(SecurityEvent.Type.LOGIN_LOCKED, request, user=known, seconds=lock_seconds)
            return LoginResult(LoginStatus.LOCKED, retry_after=lock_seconds)
        return LoginResult(LoginStatus.INVALID)

    # The password was right, so these answers reveal nothing to someone who doesn't already know it.
    throttling.clear_failures(email)
    if twofactor.is_enabled(user):
        return LoginResult(LoginStatus.TWO_FACTOR_REQUIRED, user=user)
    return LoginResult(LoginStatus.OK, user=user)


def _known_user(email):
    from django.contrib.auth import get_user_model

    return get_user_model()._default_manager.filter(email=email).first()


def start_two_factor(request, user, remember, next_url):
    """Password accepted; remember who is half-signed-in until they enter their code."""
    request.session.cycle_key()
    request.session[PENDING_2FA_SESSION_KEY] = {
        "user_id": user.pk,
        "backend": user.backend,
        "remember": bool(remember),
        "next": next_url or "",
        "started": int(time.time()),
    }


def pending_two_factor(request):
    """The pending 2FA state, or None if there is none or it has expired."""
    pending = request.session.get(PENDING_2FA_SESSION_KEY)
    if not pending:
        return None
    if time.time() - pending.get("started", 0) > settings.ACCOUNTS_TWO_FACTOR_TIMEOUT:
        request.session.pop(PENDING_2FA_SESSION_KEY, None)
        return None
    return pending


def complete_login(request, user, remember=False, backend=None):
    """Sign the user in (login() rotates the session key) and record it."""
    request.session.pop(PENDING_2FA_SESSION_KEY, None)
    login(request, user, backend=backend)
    request.session.set_expiry(settings.ACCOUNTS_REMEMBER_ME_AGE if remember else 0)
    sessions.track(request, user)
    _flag_new_location(request, user)
    record_event(SecurityEvent.Type.LOGIN_SUCCEEDED, request, user=user)


def _flag_new_location(request, user):
    """Email the user when they sign in from an IP address not seen in the last 90 days."""
    ip = get_client_ip(request)
    seen_before = SecurityEvent.objects.filter(
        user=user,
        event_type=SecurityEvent.Type.LOGIN_SUCCEEDED,
        created_at__gte=timezone.now() - timedelta(days=90),
    )
    if not seen_before.exists():
        return  # first sign-in: nothing to compare against
    if seen_before.filter(ip_address=ip).exists():
        return
    record_event(SecurityEvent.Type.LOGIN_NEW_LOCATION, request, user=user)
    send_account_email(user, "new_login", request, ip=ip, when=timezone.now())
