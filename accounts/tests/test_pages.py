from django.urls import reverse

from accounts import twofactor
from accounts.roles import Role

from .helpers import AccountTestCase, make_user


class PageRenderTests(AccountTestCase):
    """Every account page renders with its form, labels and the account stylesheet."""

    def test_public_pages_render(self):
        for name in [
            "register", "login",
            "password_reset", "password_reset_done", "password_reset_complete", "reactivate_request",
        ]:
            with self.subTest(page=name):
                response = self.client.get(reverse(f"accounts:{name}"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "accounts.css")

    def test_signed_in_pages_render(self):
        user = make_user(role=Role.STAFF)
        self.client.force_login(user)
        for name in ["profile", "password_change", "security", "two_factor_setup", "deactivate", "delete_account"]:
            with self.subTest(page=name):
                response = self.client.get(reverse(f"accounts:{name}"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'action="/accounts/logout/"')
        twofactor.enable(user, twofactor.new_secret())
        for name in ["two_factor_disable", "two_factor_backup_codes"]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(f"accounts:{name}")).status_code, 200)

    def test_password_fields_have_toggle_and_strength_meter(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertContains(response, "data-password-toggle", count=2)
        self.assertContains(response, "data-strength-meter")
        self.assertContains(response, 'data-match="id_password1"')
        self.assertContains(response, '<label for="id_email"', html=False)

    def test_navbar_links_to_sign_in_and_account(self):
        self.assertContains(self.client.get(reverse("home")), reverse("accounts:login"))
        self.client.force_login(make_user())
        self.assertContains(self.client.get(reverse("home")), reverse("accounts:profile"))

    def test_custom_404_page(self):
        response = self.client.get("/no-such-page/")
        self.assertContains(response, "We couldn’t find that page", status_code=404)
