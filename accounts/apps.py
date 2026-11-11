from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Accounts"

    def ready(self):
        from .roles import sync_role_groups

        # Recreate the role groups and their permissions after every `migrate`,
        # so the definitions in roles.py are always what the database holds.
        post_migrate.connect(sync_role_groups, sender=self, dispatch_uid="accounts.sync_role_groups")
