from datetime import timedelta
from io import StringIO

import pyotp
from django.contrib.sessions.models import Session
from django.core import mail
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts import twofactor
from accounts.models import SecurityEvent, TOTPDevice, UserSession
from accounts.services import PENDING_2FA_SESSION_KEY

from .helpers import PASSWORD, AccountTestCase, User, link_from_last_email, make_user

PROFILE = reverse("accounts:profile")
SECURITY = reverse("accounts:security")


class ProfileTests(AccountTestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("bob@example.com", first_name="Bob")
        self.login()

    def test_profile_shows_account_information(self):
        response = self.client.get(PROFILE)
        self.assertContains(response, 'id="account-heading">Hello, Ama</h1>')
        self.assertNotContains(response, "{{")
        self.assertContains(response, "ama@example.com")
        self.assertContains(response, "Customer")
        self.assertContains(response, self.user.date_joined.strftime("%Y"))

    def test_update_names_and_phone(self):
        response = self.client.post(PROFILE, {"first_name": " Amelia ", "last_name": "Kato", "phone_number": "0751 526014"})
        self.assertRedirects(response, PROFILE)
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.last_name, self.user.phone_number), ("Amelia", "Kato", "0751 526014"))

    def test_invalid_updates_are_rejected(self):
        response = self.client.post(PROFILE, {"first_name": "", "last_name": "Kato", "phone_number": "abc"})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.context["form"].errors.get("first_name"))
        self.assertTrue(response.context["form"].errors.get("phone_number"))

    def test_sensitive_fields_cannot_be_changed(self):
        self.client.post(PROFILE, {
            "first_name": "Ama", "last_name": "Nakato", "phone_number": "",
            "email": "evil@example.com", "is_staff": "on", "is_superuser": "on",
            "is_active": "", "groups": "1", "role": "Administrator", "id": self.other.pk,
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ama@example.com")
        self.assertFalse(self.user.is_staff or self.user.is_superuser)
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.groups.filter(name="Administrator").exists())

    def test_cannot_update_another_users_profile(self):
        # Ownership never comes from the request: an id in the form is ignored.
        self.client.post(PROFILE, {"first_name": "Hacked", "last_name": "X", "phone_number": "", "pk": self.other.pk, "user": self.other.pk})
        self.other.refresh_from_db()
        self.assertEqual(self.other.first_name, "Bob")

    def test_anonymous_update_is_refused(self):
        anonymous = Client()
        response = anonymous.post(PROFILE, {"first_name": "Hacked", "last_name": "X"})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ama")


class SessionManagementTests(AccountTestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user("bob@example.com")
        self.login()
        self.phone = Client()
        self.login(client=self.phone)

    def test_security_page_lists_sessions_and_activity(self):
        response = self.client.get(SECURITY)
        self.assertEqual(len(response.context["sessions"]), 2)
        self.assertContains(response, "This device")
        self.assertContains(response, "Signed in")

    def test_revoke_one_session(self):
        phone_session = UserSession.objects.exclude(session_key=self.client.session.session_key).get(user=self.user)
        self.client.post(reverse("accounts:revoke_session", args=[phone_session.pk]))
        self.assertFalse(Session.objects.filter(session_key=phone_session.session_key).exists())
        self.assertEqual(self.phone.get(PROFILE).status_code, 302)
        self.assertEqual(self.client.get(PROFILE).status_code, 200)

    def test_cannot_revoke_another_users_session(self):
        bob = Client()
        self.login("bob@example.com", client=bob)
        bob_session = UserSession.objects.get(user=self.other)
        response = self.client.post(reverse("accounts:revoke_session", args=[bob_session.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(bob.get(PROFILE).status_code, 200)

    def test_sign_out_everywhere_else(self):
        self.client.post(reverse("accounts:revoke_other_sessions"))
        self.assertEqual(self.phone.get(PROFILE).status_code, 302)
        self.assertEqual(self.client.get(PROFILE).status_code, 200)


class TwoFactorTests(AccountTestCase):
    def setUp(self):
        self.user = make_user()

    def enable_2fa(self):
        secret = twofactor.new_secret()
        codes = twofactor.enable(self.user, secret)
        return secret, codes

    def test_setup_flow(self):
        self.login()
        page = self.client.get(reverse("accounts:two_factor_setup"))
        self.assertContains(page, "data:image/svg+xml")
        secret = self.client.session["_accounts_totp_setup_secret"]
        bad = self.client.post(reverse("accounts:two_factor_setup"), {"code": "000000"})
        self.assertTrue(bad.context["form"].errors)
        response = self.client.post(reverse("accounts:two_factor_setup"), {"code": pyotp.TOTP(secret).now()})
        self.assertEqual(len(response.context["codes"]), twofactor.BACKUP_CODE_COUNT)
        self.assertTrue(twofactor.is_enabled(self.user))
        self.assertTrue(SecurityEvent.objects.filter(user=self.user, event_type=SecurityEvent.Type.TWO_FACTOR_ENABLED).exists())

    def test_login_requires_the_second_factor(self):
        secret, _ = self.enable_2fa()
        response = self.login()
        self.assertRedirects(response, reverse("accounts:login_two_factor"))
        self.assertNotIn("_auth_user_id", self.client.session)  # not signed in yet
        self.assertEqual(self.client.get(PROFILE).status_code, 302)

        wrong = self.client.post(reverse("accounts:login_two_factor"), {"code": "123456"})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(wrong.context["form"].errors)

        response = self.client.post(reverse("accounts:login_two_factor"), {"code": pyotp.TOTP(secret).now()})
        self.assertRedirects(response, PROFILE)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_codes_cannot_be_replayed(self):
        secret, _ = self.enable_2fa()
        code = pyotp.TOTP(secret).now()
        self.assertEqual(twofactor.verify(self.user, code), "totp")
        self.assertIsNone(twofactor.verify(self.user, code))

    def test_backup_codes_work_once(self):
        _, codes = self.enable_2fa()
        self.assertEqual(twofactor.verify(self.user, codes[0].upper()), "backup")
        self.assertIsNone(twofactor.verify(self.user, codes[0]))
        self.assertEqual(twofactor.remaining_backup_codes(self.user), twofactor.BACKUP_CODE_COUNT - 1)

    def test_pending_two_factor_login_expires(self):
        self.enable_2fa()
        self.login()
        session = self.client.session
        session[PENDING_2FA_SESSION_KEY]["started"] -= 3600
        session.save()
        response = self.client.post(reverse("accounts:login_two_factor"), {"code": "123456"})
        self.assertRedirects(response, reverse("accounts:login"))

    def test_too_many_wrong_codes_restart_sign_in(self):
        self.enable_2fa()
        self.login()
        for _ in range(6):
            response = self.client.post(reverse("accounts:login_two_factor"), {"code": "000000"})
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertNotIn(PENDING_2FA_SESSION_KEY, self.client.session)

    def test_disabling_needs_password_and_code(self):
        secret, _ = self.enable_2fa()
        self.client.force_login(self.user)
        url = reverse("accounts:two_factor_disable")
        self.client.post(url, {"password": "wrong-password-1", "code": pyotp.TOTP(secret).now()})
        self.assertTrue(TOTPDevice.objects.filter(user=self.user).exists())
        self.client.post(url, {"password": PASSWORD, "code": pyotp.TOTP(secret).now()})
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())


class DeactivationAndDeletionTests(AccountTestCase):
    def setUp(self):
        self.user = make_user()
        self.login()

    def test_deactivate_and_reactivate(self):
        wrong = self.client.post(reverse("accounts:deactivate"), {"password": "wrong-password-1"})
        self.assertTrue(wrong.context["form"].errors)

        self.assertRedirects(self.client.post(reverse("accounts:deactivate"), {"password": PASSWORD}), reverse("home"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertEqual(self.client.get(PROFILE).status_code, 302)
        self.assertEqual(self.login().status_code, 400)  # generic error

        self.client.post(reverse("accounts:reactivate_request"), {"email": "ama@example.com"})
        link = link_from_last_email("/accounts/reactivate/")
        self.assertEqual(self.client.get(link).status_code, 200)  # GET only shows a button
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertRedirects(self.client.post(link), reverse("accounts:login"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.client.post(link).status_code, 400)  # single use
        self.assertRedirects(self.login(), PROFILE)

    def test_admin_suspended_account_cannot_self_reactivate(self):
        self.user.is_active = False
        self.user.deactivation_reason = User.DeactivationReason.ADMIN
        self.user.save()
        mail.outbox.clear()
        self.client.post(reverse("accounts:reactivate_request"), {"email": "ama@example.com"})
        self.assertEqual(len(mail.outbox), 0)

    def test_delete_account(self):
        bad = self.client.post(reverse("accounts:delete_account"), {"password": PASSWORD, "confirm": "delete"})
        self.assertTrue(bad.context["form"].errors.get("confirm"))
        response = self.client.post(reverse("accounts:delete_account"), {"password": PASSWORD, "confirm": "DELETE"})
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(User.objects.filter(email="ama@example.com").exists())
        self.assertFalse(SecurityEvent.objects.filter(user_id=self.user.pk).exists())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_superuser_cannot_self_delete_from_account_page(self):
        admin = User.objects.create_superuser("root@example.com", PASSWORD, first_name="R", last_name="T")
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("accounts:delete_account")).status_code, 403)


class PruneCommandTests(AccountTestCase):
    def test_prunes_old_records_with_batch_cap(self):
        user = make_user()
        old = timezone.now() - timedelta(days=400)
        for _ in range(3):
            SecurityEvent.objects.create(user=user, event_type=SecurityEvent.Type.LOGIN_SUCCEEDED, created_at=old)
        recent = SecurityEvent.objects.create(user=user, event_type=SecurityEvent.Type.LOGIN_SUCCEEDED)
        out = StringIO()
        call_command("prune_account_records", batch_size=2, stdout=out)
        self.assertIn("security events: deleted 2 (batch limit reached", out.getvalue())
        call_command("prune_account_records", stdout=StringIO())
        self.assertEqual(list(SecurityEvent.objects.all()), [recent])
