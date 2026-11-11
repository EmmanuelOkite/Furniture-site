from django.conf import settings
from django.core import mail
from django.test import Client, override_settings
from django.urls import reverse

from accounts import throttling
from accounts.models import LoginLockout, SecurityEvent, UserSession

from .helpers import PASSWORD, AccountTestCase, make_user

LOGIN = reverse("accounts:login")
PROFILE = reverse("accounts:profile")
GENERIC_ERROR = "Email or password is incorrect."


class LoginTests(AccountTestCase):
    def setUp(self):
        self.user = make_user()

    def test_successful_login(self):
        response = self.login()
        self.assertRedirects(response, PROFILE)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.assertTrue(UserSession.objects.filter(user=self.user).exists())
        self.assertTrue(SecurityEvent.objects.filter(user=self.user, event_type=SecurityEvent.Type.LOGIN_SUCCEEDED).exists())
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_email_is_case_insensitive(self):
        self.assertRedirects(self.login(email=" AMA@Example.com "), PROFILE)

    def test_session_id_changes_on_login(self):
        session = self.client.session
        session["visited"] = True
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        before = session.session_key
        self.login()
        self.assertNotEqual(self.client.cookies[settings.SESSION_COOKIE_NAME].value, before)

    def test_invalid_credentials_give_the_same_answer_for_unknown_emails(self):
        wrong_password = self.login(password="wrong-password-123")
        unknown_email = self.login(email="nobody@example.com")
        for response in (wrong_password, unknown_email):
            self.assertEqual(response.status_code, 400)
            self.assertContains(response, GENERIC_ERROR, status_code=400)
            self.assertNotIn("_auth_user_id", self.client.session)

    def test_account_without_email_verification_can_sign_in(self):
        make_user("new@example.com", verified=False)
        self.assertRedirects(self.login(email="new@example.com"), PROFILE)

    def test_inactive_account_gets_the_generic_error(self):
        self.user.is_active = False
        self.user.save()
        self.assertContains(self.login(), GENERIC_ERROR, status_code=400)

    def test_remember_me_controls_session_lifetime(self):
        self.login()
        self.assertTrue(self.client.session.get_expire_at_browser_close())
        other = Client()
        self.login(client=other, remember_me="on")
        self.assertFalse(other.session.get_expire_at_browser_close())

    def test_safe_next_is_followed_and_external_next_is_ignored(self):
        security = reverse("accounts:security")
        self.assertRedirects(self.login(next=security), security)
        self.client.logout()
        self.assertRedirects(self.login(next="https://evil.example.com/"), PROFILE)

    def test_new_network_sign_in_alerts_the_user(self):
        self.client.post(LOGIN, {"email": "ama@example.com", "password": PASSWORD}, REMOTE_ADDR="10.0.0.1")
        self.assertEqual(len(mail.outbox), 0)  # first sign-in: nothing to compare with
        Client().post(LOGIN, {"email": "ama@example.com", "password": PASSWORD}, REMOTE_ADDR="10.0.0.2")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("New sign-in", mail.outbox[0].subject)
        self.assertTrue(SecurityEvent.objects.filter(user=self.user, event_type=SecurityEvent.Type.LOGIN_NEW_LOCATION).exists())

    def test_failed_logins_do_not_log_the_password(self):
        with self.assertLogs("accounts.security", level="INFO") as logs:
            self.login(password="Secret-Guess-999")
        self.assertNotIn("Secret-Guess-999", "\n".join(logs.output))
        self.assertNotIn("ama@example.com", "\n".join(logs.output))


class BruteForceProtectionTests(AccountTestCase):
    def setUp(self):
        self.user = make_user()

    def test_account_locks_after_repeated_failures(self):
        for _ in range(settings.ACCOUNTS_LOCKOUT_THRESHOLD - 1):
            self.assertEqual(self.login(password="wrong-password-123").status_code, 400)
        locked = self.login(password="wrong-password-123")
        self.assertEqual(locked.status_code, 429)
        self.assertContains(locked, "Too many sign-in attempts", status_code=429)
        # Even the right password is refused while locked.
        response = self.login()
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(SecurityEvent.objects.filter(user=self.user, event_type=SecurityEvent.Type.LOGIN_LOCKED).exists())

    def test_unknown_emails_lock_the_same_way(self):
        for _ in range(settings.ACCOUNTS_LOCKOUT_THRESHOLD):
            response = self.login(email="nobody@example.com", password="wrong-password-123")
        self.assertEqual(response.status_code, 429)

    def test_lockout_grows_progressively(self):
        threshold = settings.ACCOUNTS_LOCKOUT_THRESHOLD
        for _ in range(threshold - 1):
            self.assertEqual(throttling.register_failure("x@example.com"), 0)
        self.assertEqual(throttling.register_failure("x@example.com"), 60)
        self.assertEqual(throttling.register_failure("x@example.com"), 120)
        self.assertEqual(throttling.register_failure("x@example.com"), 240)
        for _ in range(20):
            seconds = throttling.register_failure("x@example.com")
        self.assertEqual(seconds, settings.ACCOUNTS_LOCKOUT_MAX_SECONDS)

    def test_lockout_table_stores_no_email(self):
        self.login(password="wrong-password-123")
        self.assertNotIn("ama", LoginLockout.objects.get().key)

    def test_successful_login_clears_failures(self):
        self.login(password="wrong-password-123")
        self.login()
        self.assertFalse(LoginLockout.objects.exists())

    @override_settings(ACCOUNTS_RATE_LIMITS={**settings.ACCOUNTS_RATE_LIMITS, "login:ip": (3, 900)})
    def test_login_is_throttled_per_ip(self):
        for i in range(3):
            self.login(email=f"user{i}@example.com", password="wrong-password-123")
        response = self.login()
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)


class LogoutAndAccessTests(AccountTestCase):
    def setUp(self):
        self.user = make_user()

    def test_logout_ends_the_session(self):
        self.login()
        session_key = self.client.session.session_key
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(UserSession.objects.filter(session_key=session_key).exists())
        from django.contrib.sessions.models import Session

        self.assertFalse(Session.objects.filter(session_key=session_key).exists())
        self.assertRedirects(self.client.get(PROFILE), f"{LOGIN}?next={PROFILE}")

    def test_logout_requires_post(self):
        self.login()
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_protected_pages_require_login(self):
        for name in ["profile", "security", "password_change", "two_factor_setup", "deactivate", "delete_account"]:
            with self.subTest(page=name):
                url = reverse(f"accounts:{name}")
                self.assertRedirects(self.client.get(url), f"{LOGIN}?next={url}")

    def test_admin_login_goes_through_account_sign_in(self):
        response = self.client.get("/admin/login/?next=/admin/")
        self.assertRedirects(response, f"{LOGIN}?next=%2Fadmin%2F", fetch_redirect_response=False)

    def test_signed_in_customer_sent_to_admin_does_not_loop(self):
        self.login()
        response = self.client.get(f"{LOGIN}?next=/admin/")
        self.assertRedirects(response, PROFILE)


class CsrfAndHeaderTests(AccountTestCase):
    def setUp(self):
        self.user = make_user()

    def test_login_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(LOGIN, {"email": "ama@example.com", "password": PASSWORD})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("_auth_user_id", client.session)

    def test_login_with_csrf_token_succeeds(self):
        client = Client(enforce_csrf_checks=True)
        page = client.get(LOGIN)
        token = page.context["csrf_token"]
        response = client.post(LOGIN, {"email": "ama@example.com", "password": PASSWORD, "csrfmiddlewaretoken": token})
        self.assertRedirects(response, PROFILE)

    def test_profile_update_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(PROFILE, {"first_name": "Hacked", "last_name": "X", "phone_number": ""})
        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ama")

    def test_security_headers(self):
        response = self.client.get(LOGIN)
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Referrer-Policy"], "same-origin")
        csp = response["Content-Security-Policy"]
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertRegex(csp, r"script-src 'self' 'nonce-[\w+/=-]+'")
        self.assertIn("no-cache", response["Cache-Control"])
        # The inline script carries the same nonce.
        nonce = csp.split("'nonce-")[1].split("'")[0]
        self.assertContains(response, f'nonce="{nonce}"')

    def test_user_input_is_escaped(self):
        self.user.first_name = "<script>alert(1)</script>"
        self.user.save()
        self.client.force_login(self.user)
        response = self.client.get(PROFILE)
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
