from django.core import mail
from django.test import override_settings
from django.urls import reverse

from accounts.models import SecurityEvent
from accounts.roles import Role, get_role

from .helpers import PASSWORD, AccountTestCase, User, make_user

REGISTER = reverse("accounts:register")


def signup_data(**overrides):
    data = {
        "first_name": "Ama",
        "last_name": "Nakato",
        "email": "ama@example.com",
        "phone_number": "+256 751 526 014",
        "password1": PASSWORD,
        "password2": PASSWORD,
    }
    data.update(overrides)
    return data


class RegistrationTests(AccountTestCase):
    def test_successful_registration(self):
        response = self.client.post(REGISTER, signup_data(email="  Ama@Example.COM "))
        self.assertRedirects(response, reverse("accounts:login"))

        user = User.objects.get()
        self.assertEqual(user.email, "ama@example.com")  # normalised
        self.assertEqual(user.phone_number, "+256 751 526 014")
        self.assertIsNotNone(user.date_joined)
        self.assertFalse(user.is_staff)
        self.assertEqual(get_role(user), Role.CUSTOMER)
        # Hashed, never stored as plain text.
        self.assertNotIn(PASSWORD, user.password)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(len(mail.outbox), 0)  # no verification email
        self.assertTrue(SecurityEvent.objects.filter(user=user, event_type=SecurityEvent.Type.REGISTERED).exists())

    def test_new_account_can_sign_in_immediately(self):
        self.client.post(REGISTER, signup_data())
        response = self.login()
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 200)

    def test_duplicate_email_is_rejected(self):
        make_user()
        response = self.client.post(REGISTER, signup_data(email="AMA@example.com"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("already exists", str(response.context["form"].errors["email"]))
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_email_is_rejected(self):
        response = self.client.post(REGISTER, signup_data(email="not-an-email"))
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "email", "Enter a valid email address.")
        self.assertFalse(User.objects.exists())

    def test_weak_passwords_are_rejected(self):
        for weak in ["password123", "short1!", "12345678901234", "ama@example.com"]:
            with self.subTest(password=weak):
                response = self.client.post(REGISTER, signup_data(password1=weak, password2=weak))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors.get("password1"))
        self.assertFalse(User.objects.exists())

    def test_password_mismatch_is_rejected(self):
        response = self.client.post(REGISTER, signup_data(password2=PASSWORD + "x"))
        self.assertFormError(response.context["form"], "password2", "The two passwords don’t match.")
        self.assertFalse(User.objects.exists())

    def test_invalid_phone_is_rejected(self):
        response = self.client.post(REGISTER, signup_data(phone_number="call me"))
        self.assertTrue(response.context["form"].errors.get("phone_number"))

    def test_privileged_fields_cannot_be_mass_assigned(self):
        self.client.post(REGISTER, signup_data(is_staff="on", is_superuser="on", email_verified_at="2020-01-01"))
        user = User.objects.get()
        self.assertFalse(user.is_staff or user.is_superuser)

    @override_settings(ACCOUNTS_RATE_LIMITS={"register:ip": (2, 3600)})
    def test_registration_is_rate_limited(self):
        for i in range(2):
            self.client.post(REGISTER, signup_data(email=f"user{i}@example.com"))
        response = self.client.post(REGISTER, signup_data(email="third@example.com"))
        self.assertEqual(response.status_code, 429)
        self.assertFalse(User.objects.filter(email="third@example.com").exists())
