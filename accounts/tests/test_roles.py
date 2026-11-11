from django.contrib.auth.models import Group
from django.urls import reverse

from accounts.models import SecurityEvent
from accounts.roles import ROLE_PERMISSIONS, Role, get_role, role_change_error

from .helpers import PASSWORD, AccountTestCase, User, make_user


def change_form_data(user, **overrides):
    data = {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone_number": user.phone_number,
        "role": get_role(user) or Role.CUSTOMER,
        "is_active": "on" if user.is_active else "",
    }
    data.update(overrides)
    return {k: v for k, v in data.items() if v != ""}


class RoleDefinitionTests(AccountTestCase):
    def test_role_groups_have_the_defined_permissions(self):
        for role, perms in ROLE_PERMISSIONS.items():
            group = Group.objects.get(name=role.value)
            granted = {f"{p.content_type.app_label}.{p.codename}" for p in group.permissions.select_related("content_type")}
            self.assertEqual(granted, set(perms))

    def test_customers_have_no_model_permissions(self):
        user = make_user()
        self.assertFalse(user.is_staff)
        self.assertEqual(user.get_all_permissions(), set())

    def test_role_change_rules(self):
        superuser = User.objects.create_superuser("root@example.com", PASSWORD, first_name="R", last_name="T")
        admin = make_user("admin@example.com", role=Role.ADMINISTRATOR)
        staff = make_user("staff@example.com", role=Role.STAFF)
        customer = make_user("cust@example.com")

        self.assertIsNone(role_change_error(admin, customer, Role.STAFF))
        self.assertIn("own role", role_change_error(admin, admin, Role.STAFF))
        self.assertIn("superuser", role_change_error(admin, customer, Role.ADMINISTRATOR))
        self.assertIn("superuser", role_change_error(admin, superuser, Role.CUSTOMER))
        self.assertIn("permission", role_change_error(staff, customer, Role.STAFF))
        self.assertIn("permission", role_change_error(customer, customer, Role.ADMINISTRATOR))
        self.assertIsNone(role_change_error(superuser, customer, Role.ADMINISTRATOR))


class AdminPermissionTests(AccountTestCase):
    def setUp(self):
        self.admin = make_user("admin@example.com", role=Role.ADMINISTRATOR)
        self.staff = make_user("staff@example.com", role=Role.STAFF)
        self.customer = make_user("cust@example.com")
        self.superuser = User.objects.create_superuser("root@example.com", PASSWORD, first_name="R", last_name="T")

    def user_change_url(self, user):
        return reverse("admin:accounts_user_change", args=[user.pk])

    def test_customer_cannot_open_the_admin(self):
        self.client.force_login(self.customer)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_staff_can_manage_products_but_not_users(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("admin:furnitureapp_product_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:accounts_user_changelist")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:accounts_securityevent_changelist")).status_code, 403)

    def test_administrator_can_promote_customer_to_staff(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.user_change_url(self.customer), change_form_data(self.customer, role=Role.STAFF))
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["adminform"].form.errors)
        self.customer.refresh_from_db()
        self.assertEqual(get_role(self.customer), Role.STAFF)
        self.assertTrue(self.customer.is_staff)
        event = SecurityEvent.objects.get(user=self.customer, event_type=SecurityEvent.Type.ROLE_CHANGED)
        self.assertEqual(event.details["changed_by"], self.admin.pk)

    def test_administrator_cannot_create_administrators(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.user_change_url(self.customer), change_form_data(self.customer, role=Role.ADMINISTRATOR))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Only a superuser", str(response.context["adminform"].form.errors))
        self.assertEqual(get_role(self.customer), Role.CUSTOMER)

    def test_administrator_cannot_change_own_role_or_flags(self):
        self.client.force_login(self.admin)
        self.client.post(self.user_change_url(self.admin), change_form_data(self.admin, role=Role.CUSTOMER, is_superuser="on"))
        self.admin.refresh_from_db()
        self.assertEqual(get_role(self.admin), Role.ADMINISTRATOR)
        self.assertFalse(self.admin.is_superuser)

    def test_administrator_cannot_grant_superuser(self):
        self.client.force_login(self.admin)
        self.client.post(self.user_change_url(self.customer), change_form_data(self.customer, is_superuser="on", is_staff="on"))
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_superuser)
        self.assertFalse(self.customer.is_staff)

    def test_administrator_cannot_edit_a_superuser(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.user_change_url(self.superuser), change_form_data(self.superuser, first_name="Hacked"))
        self.assertEqual(response.status_code, 403)
        self.superuser.refresh_from_db()
        self.assertEqual(self.superuser.first_name, "R")

    def test_administrator_cannot_set_other_peoples_passwords(self):
        self.client.force_login(self.admin)
        url = reverse("admin:auth_user_password_change", args=[self.customer.pk])
        response = self.client.post(url, {"password1": "Another-Strong-Pass-1", "password2": "Another-Strong-Pass-1"})
        self.assertEqual(response.status_code, 403)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password(PASSWORD))

    def test_superuser_can_create_administrators(self):
        self.client.force_login(self.superuser)
        response = self.client.post(self.user_change_url(self.customer), change_form_data(self.customer, role=Role.ADMINISTRATOR))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(get_role(self.customer), Role.ADMINISTRATOR)

    def test_admin_deactivation_is_recorded_as_suspension(self):
        self.client.force_login(self.admin)
        data = change_form_data(self.customer)
        data.pop("is_active")
        self.client.post(self.user_change_url(self.customer), data)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)
        self.assertEqual(self.customer.deactivation_reason, User.DeactivationReason.ADMIN)
