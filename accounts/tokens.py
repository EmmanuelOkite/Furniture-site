"""
Signed, time-limited, single-use tokens for account reactivation links.

The token carries the user id and a fingerprint of the account state the link
is meant to change (active status). Once that state
changes the fingerprint no longer matches, so each link works only once.
Password reset tokens use Django's own generator (see views.py).
"""

from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.utils.crypto import constant_time_compare, salted_hmac

REACTIVATE = "reactivate"

_MAX_AGE_SETTINGS = {
    REACTIVATE: "ACCOUNTS_REACTIVATION_TIMEOUT",
}


def _state(user, purpose):
    if purpose == REACTIVATE:
        deactivated = user.deactivated_at.isoformat() if user.deactivated_at else ""
        return f"{user.email}|{user.is_active}|{deactivated}"
    raise ValueError(f"Unknown token purpose: {purpose}")


def _fingerprint(user, purpose):
    return salted_hmac(f"accounts.tokens.{purpose}", f"{user.pk}|{_state(user, purpose)}").hexdigest()[:32]


def make_token(user, purpose):
    return signing.dumps({"u": user.pk, "f": _fingerprint(user, purpose)}, salt=f"accounts.{purpose}")


@dataclass
class TokenResult:
    user: object = None
    expired: bool = False

    @property
    def valid(self):
        return self.user is not None


def check_token(token, purpose):
    max_age = getattr(settings, _MAX_AGE_SETTINGS[purpose])
    try:
        data = signing.loads(token, salt=f"accounts.{purpose}", max_age=max_age)
    except signing.SignatureExpired:
        return TokenResult(expired=True)
    except signing.BadSignature:
        return TokenResult()
    if not isinstance(data, dict):
        return TokenResult()
    user = get_user_model()._default_manager.filter(pk=data.get("u")).first()
    if user is None or not constant_time_compare(str(data.get("f", "")), _fingerprint(user, purpose)):
        return TokenResult()
    return TokenResult(user=user)
