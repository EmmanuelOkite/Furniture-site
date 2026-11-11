import re
import unicodedata

from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _, ngettext


def normalize_email_address(email):
    """Canonical form used for storage and lookups: NFKC, trimmed, lower-case."""
    return unicodedata.normalize("NFKC", email or "").strip().lower()


_PHONE_ALLOWED = re.compile(r"^\+?[0-9 ()\-]+$")


def validate_phone_number(value):
    """Accept international formats such as +256 751 526 014 or 0751-526014."""
    digits = re.sub(r"\D", "", value)
    if not _PHONE_ALLOWED.match(value) or not 7 <= len(digits) <= 15:
        raise ValidationError(
            _("Enter a valid phone number, e.g. +256 751 526 014."), code="invalid_phone"
        )


class PasswordHistoryValidator:
    """
    Reject the user's current password and their last `history` passwords.

    Django calls `validate()` from every password-setting form and
    `password_changed()` after a new password is saved, so this one class
    covers sign-up, change, reset and the admin.
    """

    def __init__(self, history=5):
        self.history = history

    def _recent_hashes(self, user):
        from .models import PasswordHistory

        return list(
            PasswordHistory.objects.filter(user=user)
            .order_by("-created_at", "-pk")
            .values_list("password_hash", flat=True)[: self.history]
        )

    def validate(self, password, user=None):
        if user is None or user.pk is None:
            return
        hashes = self._recent_hashes(user)
        if user.password and user.password not in hashes:
            hashes.append(user.password)
        if any(check_password(password, h) for h in hashes):
            raise ValidationError(
                ngettext(
                    "You cannot reuse your previous password.",
                    "You cannot reuse any of your last %(count)d passwords.",
                    self.history,
                ),
                code="password_reused",
                params={"count": self.history},
            )

    def password_changed(self, password, user):
        from .models import PasswordHistory

        if user.pk is None or not user.has_usable_password():
            return
        PasswordHistory.objects.create(user=user, password_hash=user.password)
        stale = (
            PasswordHistory.objects.filter(user=user)
            .order_by("-created_at", "-pk")
            .values_list("pk", flat=True)[self.history :]
        )
        PasswordHistory.objects.filter(pk__in=list(stale)).delete()

    def get_help_text(self):
        return ngettext(
            "Your password can’t be your previous password.",
            "Your password can’t be one of your last %(count)d passwords.",
            self.history,
        ) % {"count": self.history}
