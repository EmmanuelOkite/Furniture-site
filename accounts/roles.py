"""
Role-based access control built on Django Groups.

A user's role is the role group they belong to. `ROLE_PERMISSIONS` is the
single source of truth for what each role may do; `sync_role_groups` writes it
to the database after every migration.
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.db import DEFAULT_DB_ALIAS, models, transaction


class Role(models.TextChoices):
    ADMINISTRATOR = "Administrator", "Administrator"
    STAFF = "Staff", "Staff"
    CUSTOMER = "Customer", "Customer"


DEFAULT_ROLE = Role.CUSTOMER

# Roles whose members may sign in to the Django admin.
STAFF_ROLES = frozenset({Role.ADMINISTRATOR, Role.STAFF})

ROLE_PERMISSIONS = {
    # Customers manage only their own account, through the account pages.
    Role.CUSTOMER: [],
    # Store staff look after the catalogue but cannot see customer accounts.
    Role.STAFF: [
        "furnitureapp.view_product",
        "furnitureapp.add_product",
        "furnitureapp.change_product",
    ],
    # Administrators also manage customer and staff accounts and read the audit log.
    # Granting the Administrator role or superuser status is reserved for superusers.
    Role.ADMINISTRATOR: [
        "furnitureapp.view_product",
        "furnitureapp.add_product",
        "furnitureapp.change_product",
        "furnitureapp.delete_product",
        "accounts.view_user",
        "accounts.change_user",
        "accounts.assign_role",
        "accounts.view_securityevent",
    ],
}


def sync_role_groups(using=DEFAULT_DB_ALIAS, **kwargs):
    """Create the role groups and set their permissions (idempotent)."""
    # Permissions for every app must exist before they can be attached to groups.
    for app_config in global_apps.get_app_configs():
        create_permissions(app_config, verbosity=0, using=using)

    for role, perm_names in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.using(using).get_or_create(name=role.value)
        perms = []
        for name in perm_names:
            app_label, codename = name.split(".")
            perms.append(
                Permission.objects.using(using).get(content_type__app_label=app_label, codename=codename)
            )
        group.permissions.set(perms)


def get_role(user):
    """The user's role, or None if they have none (e.g. a superuser created from the shell)."""
    if not user.pk:
        return None
    name = user.groups.filter(name__in=Role.values).values_list("name", flat=True).first()
    return Role(name) if name else None


@transaction.atomic
def set_role(user, role):
    """Put the user in exactly one role group and keep is_staff in step with it."""
    role = Role(role)
    user.groups.remove(*Group.objects.filter(name__in=Role.values))
    user.groups.add(Group.objects.get(name=role.value))
    is_staff = role in STAFF_ROLES or user.is_superuser
    if user.is_staff != is_staff:
        user.is_staff = is_staff
        user.save(update_fields=["is_staff"])


def role_change_error(actor, target, new_role):
    """
    Why `actor` may not give `target` the role `new_role`, or None if allowed.

    Prevents privilege escalation: nobody changes their own role, and only
    superusers can create Administrators or change a superuser's/Administrator's role.
    """
    new_role = Role(new_role)
    current = get_role(target)
    if not actor.has_perm("accounts.assign_role"):
        return "You do not have permission to assign roles."
    if actor.pk == target.pk:
        return "You cannot change your own role."
    if not actor.is_superuser:
        if target.is_superuser:
            return "Only a superuser can change a superuser's role."
        if Role.ADMINISTRATOR in (new_role, current):
            return "Only a superuser can grant or remove the Administrator role."
    return None
