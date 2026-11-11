from datetime import datetime, timedelta
from unittest import mock

from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.core import mail
from django.test import Client, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts import throttling
from accounts.models import SecurityEvent

from .helpers import NEW_PASSWORD, PASSWORD, AccountTestCase, link_from_last_email, make_user

RESET = reverse("accounts:password_reset")
CHANGE = reverse("accounts:password_change")


class PasswordResetTests(AccountTestCase):
    def setUp(self):
        self.user = make_user()

    def request_reset(self, email="ama@example.com"):
        return self.client.post(RESET, {"email": email})

    def follow_reset_link(self, link):
        # Django moves the token into the session and redirects to a token-free URL.
        response = self.client.get(link)
        self.assertEqual(response.status_code, 302)
        return response["Location"]

    def test_password_reset_end_to_end(self):
        other_device = Client()
        self.login(client=other_device)

        self.assertRedirects(self.request_reset(" AMA@example.com"), reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn(PASSWORD, mail.outbox[0].body)
        set_password_url = self.follow_reset_link(link_from_last_email("/accounts/password/reset/"))
        response = self.client.post(set_password_url, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD})
        self.assertRedirects(response, reverse("accounts:password_reset_complete"))

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        # Every existing session is ended.
        self.assertRedirects(other_device.get(reverse("accounts:profile")), f"{reverse('accounts:login')}?next=/accounts/profile/")
        self.assertTrue(SecurityEvent.objects.filter(user=self.user, event_type=SecurityEvent.Type.PASSWORD_RESET).exists())
        self.assertRedirects(self.login(password=NEW_PASSWORD), reverse("accounts:profile"))

    def test_unknown_email_gets_the_same_response_and_no_email(self):
        self.assertRedirects(self.request_reset("nobody@example.com"), reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_link_is_single_use(self):
        self.request_reset()
        link = link_from_last_email("/accounts/password/reset/")
        set_password_url = self.follow_reset_link(link)
        self.client.post(set_password_url, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD})
        response = self.client.get(link, follow=True)
        self.assertFalse(response.context["validlink"])

    def test_expired_reset_link(self):
        two_hours_ago = datetime.now() - timedelta(hours=2)
        with mock.patch.object(PasswordResetTokenGenerator, "_now", return_value=two_hours_ago):
            token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        url = reverse("accounts:password_reset_confirm", args=[uid, token])
        response = self.client.get(url, follow=True)
        self.assertFalse(response.context["validlink"])
        self.assertContains(response, "This link isn’t valid")

    def test_new_password_must_be_confirmed_and_strong(self):
        self.request_reset()
        url = self.follow_reset_link(link_from_last_email("/accounts/password/reset/"))
        mismatch = self.client.post(url, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD + "x"})
        self.assertTrue(mismatch.context["form"].errors.get("new_password2"))
        weak = self.client.post(url, {"new_password1": "password123", "new_password2": "password123"})
        # Django reports validator errors on the confirmation field.
        self.assertIn("too common", str(weak.context["form"].errors))

    def test_reset_cannot_reuse_the_current_password(self):
        self.request_reset()
        url = self.follow_reset_link(link_from_last_email("/accounts/password/reset/"))
        response = self.client.post(url, {"new_password1": PASSWORD, "new_password2": PASSWORD})
        self.assertIn("reuse", str(response.context["form"].errors["new_password2"]))

    def test_reset_verifies_email_and_clears_lockout(self):
        user = make_user("new@example.com", verified=False)
        for _ in range(5):
            throttling.register_failure("new@example.com")
        self.request_reset("new@example.com")
        url = self.follow_reset_link(link_from_last_email("/accounts/password/reset/"))
        self.client.post(url, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD})
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        self.assertEqual(throttling.lockout_remaining("new@example.com"), 0)

    @override_settings(ACCOUNTS_RATE_LIMITS={"password_reset:ip": (50, 3600), "password_reset:id": (2, 3600)})
    def test_reset_requests_are_rate_limited_per_email(self):
        self.request_reset()
        self.request_reset()
        self.assertEqual(self.request_reset().status_code, 429)
        self.assertEqual(len(mail.outbox), 2)


class PasswordChangeTests(AccountTestCase):
    def setUp(self):
        self.user = make_user()
        self.login()

    def change(self, old=PASSWORD, new=NEW_PASSWORD, confirm=None):
        return self.client.post(
            CHANGE, {"old_password": old, "new_password1": new, "new_password2": confirm or new}
        )

    def test_change_password_keeps_this_session_and_ends_others(self):
        other_device = Client()
        self.login(client=other_device)
        response = self.change()
        self.assertRedirects(response, reverse("accounts:security"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 200)
        self.assertEqual(other_device.get(reverse("accounts:profile")).status_code, 302)
        self.assertIn("was just changed", mail.outbox[-1].body)

    def test_wrong_current_password_is_rejected(self):
        response = self.change(old="not-my-password")
        self.assertTrue(response.context["form"].errors.get("old_password"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_mismatched_confirmation_is_rejected(self):
        response = self.change(confirm=NEW_PASSWORD + "x")
        self.assertTrue(response.context["form"].errors.get("new_password2"))

    def test_previous_passwords_cannot_be_reused(self):
        self.change()
        response = self.change(old=NEW_PASSWORD, new=PASSWORD)
        self.assertIn("reuse", str(response.context["form"].errors))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
