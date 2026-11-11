"""Request metadata, audit logging and hashing helpers shared by the accounts app."""

import ipaddress
import logging

from django.conf import settings
from django.utils.crypto import salted_hmac

from .models import SecurityEvent

logger = logging.getLogger("accounts.security")


def _valid_ip(value):
    try:
        return str(ipaddress.ip_address(value.strip()))
    except (ValueError, AttributeError):
        return None


def get_client_ip(request):
    """
    The client's IP address.

    X-Forwarded-For can be forged by the client, so it is only read when
    ACCOUNTS_TRUSTED_PROXY_COUNT says how many proxies in front of the app
    append to it; the entry those proxies added is used.
    """
    proxies = settings.ACCOUNTS_TRUSTED_PROXY_COUNT
    if proxies > 0:
        forwarded = [p for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",") if p.strip()]
        if len(forwarded) >= proxies:
            ip = _valid_ip(forwarded[-proxies])
            if ip:
                return ip
    return _valid_ip(request.META.get("REMOTE_ADDR", ""))


def get_user_agent(request):
    return request.META.get("HTTP_USER_AGENT", "")[:255]


def keyed_hash(value, purpose):
    """HMAC of `value`, so throttle tables never hold raw emails or IPs."""
    return salted_hmac(f"accounts.{purpose}", str(value), algorithm="sha256").hexdigest()


def record_event(event_type, request=None, user=None, **details):
    """Save an audit event and write it to the security log (without secrets or emails)."""
    ip = get_client_ip(request) if request is not None else None
    event = SecurityEvent.objects.create(
        user=user if user is not None and user.pk else None,
        event_type=event_type,
        ip_address=ip,
        user_agent=get_user_agent(request) if request is not None else "",
        details=details,
    )
    level = logging.WARNING if event_type in WARNING_EVENTS else logging.INFO
    logger.log(
        level,
        "security_event type=%s user_id=%s ip=%s",
        event_type,
        user.pk if user is not None else None,
        ip,
    )
    return event


WARNING_EVENTS = frozenset(
    {
        SecurityEvent.Type.LOGIN_LOCKED,
        SecurityEvent.Type.LOGIN_NEW_LOCATION,
        SecurityEvent.Type.TWO_FACTOR_FAILED,
        SecurityEvent.Type.ROLE_CHANGED,
    }
)
