from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from . import throttling
from .models import SecurityEvent, User
from .roles import Role, get_role, role_change_error, set_role
from .security import record_event


class UserCreationAdminForm(AdminUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")


class UserChangeAdminForm(UserChangeForm):
    """Django's change form (password shown read-only as a hash summary) plus a Role field."""

    role = forms.ChoiceField(choices=Role.choices, help_text="Sets the user’s permissions and admin access.")

    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
        field_classes = {}

    # Set by UserAdmin.get_form so role changes can be checked against the acting user.
    acting_user = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "role" in self.fields:
            self.fields["role"].initial = get_role(self.instance) or Role.CUSTOMER

    def clean_role(self):
        role = self.cleaned_data["role"]
        if role != (get_role(self.instance) or Role.CUSTOMER):
            error = role_change_error(self.acting_user, self.instance, role)
            if error:
                raise forms.ValidationError(error)
        return role


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeAdminForm
    add_form = UserCreationAdminForm
    ordering = ("-date_joined",)
    list_display = ("email", "first_name", "last_name", "role_name", "is_active", "date_joined", "last_login")
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("email", "first_name", "last_name")
    readonly_fields = ("date_joined", "last_login", "updated_at", "email_verified_at", "deactivated_at", "deactivation_reason")
    filter_horizontal = ("user_permissions",)
    actions = ["clear_login_lockout"]
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "first_name", "last_name", "usable_password", "password1", "password2")}),
    )

    @admin.display(description="Role")
    def role(self, obj):
        # Shown when the Role field is read-only for the current admin.
        return self.role_name(obj)

    @admin.display(description="Role")
    def role_name(self, obj):
        return get_role(obj) or ("Superuser" if obj.is_superuser else "—")

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        access = ["role", "is_active"]
        if request.user.is_superuser:
            # Roles are managed through the Role field only, so groups are not edited directly.
            access += ["is_staff", "is_superuser", "user_permissions"]
        return (
            (None, {"fields": ("email", "password")}),
            ("Personal info", {"fields": ("first_name", "last_name", "phone_number")}),
            ("Role and access", {"fields": access}),
            ("Status", {"fields": ("email_verified_at", "deactivated_at", "deactivation_reason", "date_joined", "last_login", "updated_at")}),
        )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and (obj.pk == request.user.pk or not request.user.has_perm("accounts.assign_role")):
            readonly.append("role")
        if obj is not None and obj.pk == request.user.pk:
            readonly.append("is_active")  # nobody locks themselves out from here
        return readonly

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.acting_user = request.user
        return form

    def has_change_permission(self, request, obj=None):
        # Only superusers may edit superusers or Administrators (prevents peer takeover).
        if obj is not None and not request.user.is_superuser and obj.pk != request.user.pk:
            if obj.is_superuser or get_role(obj) == Role.ADMINISTRATOR:
                return False
        return super().has_change_permission(request, obj)

    def user_change_password(self, request, id, form_url=""):
        # Admins send a reset link instead of choosing passwords for other people.
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().user_change_password(request, id, form_url)

    def save_model(self, request, obj, form, change):
        old_role = get_role(obj) if change else None
        if change and "is_active" in form.changed_data:
            if obj.is_active:
                obj.deactivated_at, obj.deactivation_reason = None, ""
            else:
                obj.deactivated_at, obj.deactivation_reason = timezone.now(), User.DeactivationReason.ADMIN
        super().save_model(request, obj, form, change)
        if not change:
            set_role(obj, Role.CUSTOMER)
            return
        new_role = form.cleaned_data.get("role")
        if new_role and new_role != (old_role or Role.CUSTOMER):
            set_role(obj, new_role)
            record_event(
                SecurityEvent.Type.ROLE_CHANGED, request, user=obj,
                old=old_role, new=new_role, changed_by=request.user.pk,
            )

    @admin.action(description="Clear sign-in lockout for selected users", permissions=["change"])
    def clear_login_lockout(self, request, queryset):
        for user in queryset:
            throttling.clear_failures(user.email)
        self.message_user(request, f"Cleared sign-in lockout for {queryset.count()} user(s).", messages.SUCCESS)


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    """Read-only audit log."""

    list_display = ("created_at", "event_type", "user", "ip_address")
    list_filter = ("event_type", "created_at")
    search_fields = ("user__email", "ip_address")
    date_hierarchy = "created_at"
    list_select_related = ("user",)
    readonly_fields = [f.name for f in SecurityEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
