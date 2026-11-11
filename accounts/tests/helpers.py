import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.roles import Role, set_role

User = get_user_model()

PASSWORD = "Sturdy-Teak-Table-42"
NEW_PASSWORD = "Velvet-Armchair-Sunset-77"

# Tests run with DEBUG=False, where manifest static storage needs collectstatic first.
PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def make_user(email="ama@example.com", password=PASSWORD, verified=True, role=Role.CUSTOMER, **extra):
    extra.setdefault("first_name", "Ama")
    extra.setdefault("last_name", "Nakato")
    user = User.objects.create_user(email=email, password=password, **extra)
    if verified:
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])
    if role:
        set_role(user, role)
    return user


def link_from_last_email(path_fragment):
    """The first URL in the latest email that contains `path_fragment`, as a site path."""
    body = mail.outbox[-1].body
    match = re.search(r"https?://[^/\s]+(" + re.escape(path_fragment) + r"\S*)", body)
    assert match, f"No {path_fragment} link in email:\n{body}"
    return match.group(1)


@override_settings(STORAGES=PLAIN_STATIC_STORAGE)
class AccountTestCase(TestCase):
    def login(self, email="ama@example.com", password=PASSWORD, client=None, **extra):
        client = client or self.client
        return client.post("/accounts/login/", {"email": email, "password": password, **extra})
