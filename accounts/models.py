from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .validators import normalize_email_address, validate_phone_number


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=normalize_email_address(email), **extra_fields)
        user.set_password(password)  # None gives an unusable password.
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        # The person running createsuperuser controls the server; no inbox check needed.
        extra_fields.setdefault("email_verified_at", timezone.now())
        if extra_fields["is_staff"] is not True or extra_fields["is_superuser"] is not True:
            raise ValueError("A superuser must have is_staff=True and is_superuser=True.")
        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        # Used by the authentication backend: look up by the normalised address.
        return self.get(email=normalize_email_address(email))


class User(AbstractBaseUser, PermissionsMixin):
    """An account that signs in with its email address."""

    class DeactivationReason(models.TextChoices):
        SELF = "self", "Deactivated by the account holder"
        ADMIN = "admin", "Suspended by an administrator"

    email = models.EmailField(
        "email address",
        max_length=254,
        unique=True,
        error_messages={"unique": "An account with this email address already exists."},
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20, blank=True, validators=[validate_phone_number])

    is_active = models.BooleanField(
        "active",
        default=True,
        help_text="Inactive accounts cannot sign in. Untick this instead of deleting accounts.",
    )
    is_staff = models.BooleanField(
        "staff status",
        default=False,
        help_text="Can sign in to the admin site. Set automatically from the user’s role.",
    )
    email_verified_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField("date registered", default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.CharField(max_length=10, choices=DeactivationReason.choices, blank=True)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-date_joined"]
        permissions = [("assign_role", "Can assign user roles")]
        constraints = [
            # Defence in depth: emails are stored lower-case, but also refuse
            # case-variant duplicates written by any path that skips save().
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
        ]
        indexes = [models.Index(fields=["date_joined"], name="accounts_user_joined_idx")]

    def __str__(self):
        return self.email

    def clean(self):
        super().clean()
        self.email = normalize_email_address(self.email)

    def save(self, *args, **kwargs):
        self.email = normalize_email_address(self.email)
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    @property
    def is_email_verified(self):
        return self.email_verified_at is not None


class PasswordHistory(models.Model):
    """Hashes of a user's recent passwords, to stop them being reused."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_history")
    password_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "password history"
        indexes = [models.Index(fields=["user", "-created_at"], name="accounts_pwhist_user_idx")]


class SecurityEvent(models.Model):
    """Audit trail of sign-ins and account changes. Never stores passwords, tokens or session keys."""

    class Type(models.TextChoices):
        LOGIN_SUCCEEDED = "login_succeeded", "Signed in"
        LOGIN_FAILED = "login_failed", "Failed sign-in"
        LOGIN_LOCKED = "login_locked", "Sign-in temporarily locked"
        LOGIN_NEW_LOCATION = "login_new_location", "Sign-in from a new device or network"
        LOGOUT = "logout", "Signed out"
        REGISTERED = "registered", "Account created"
        EMAIL_VERIFIED = "email_verified", "Email address verified"
        PASSWORD_CHANGED = "password_changed", "Password changed"
        PASSWORD_RESET = "password_reset", "Password reset by email"
        PROFILE_UPDATED = "profile_updated", "Profile updated"
        SESSION_REVOKED = "session_revoked", "Session signed out remotely"
        TWO_FACTOR_ENABLED = "2fa_enabled", "Two-factor authentication turned on"
        TWO_FACTOR_DISABLED = "2fa_disabled", "Two-factor authentication turned off"
        TWO_FACTOR_FAILED = "2fa_failed", "Wrong two-factor code"
        BACKUP_CODE_USED = "backup_code_used", "Backup code used"
        BACKUP_CODES_REGENERATED = "backup_codes_regenerated", "New backup codes created"
        ROLE_CHANGED = "role_changed", "Role changed"
        DEACTIVATED = "deactivated", "Account deactivated"
        REACTIVATED = "reactivated", "Account reactivated"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="security_events"
    )
    event_type = models.CharField(max_length=40, choices=Type.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="accounts_event_user_idx"),
            models.Index(fields=["event_type", "-created_at"], name="accounts_event_type_idx"),
            models.Index(fields=["created_at"], name="accounts_event_created_idx"),
        ]

    def __str__(self):
        return f"{self.get_event_type_display()} at {self.created_at:%Y-%m-%d %H:%M}"


class UserSession(models.Model):
    """Links a signed-in session to its user so they can be listed and revoked."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tracked_sessions")
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"], name="accounts_session_user_idx")]


class RateLimit(models.Model):
    """Fixed-window request counter. `key` is an HMAC of the IP/email, never the raw value."""

    scope = models.CharField(max_length=50)
    key = models.CharField(max_length=64)
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["scope", "key", "window_start"], name="accounts_ratelimit_unique")
        ]
        indexes = [models.Index(fields=["window_start"], name="accounts_ratelimit_window_idx")]


class LoginLockout(models.Model):
    """
    Failed sign-in counter per email address (HMAC-keyed).

    Kept for every address tried, registered or not, so a lockout response
    never reveals whether an account exists.
    """

    key = models.CharField(max_length=64, unique=True)
    failure_count = models.PositiveIntegerField(default=0)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["last_failure_at"], name="accounts_lockout_last_idx")]


class TOTPDevice(models.Model):
    """An authenticator app linked to the account (two-factor authentication)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="totp_device")
    secret = models.CharField(max_length=64)
    # Last 30-second time step accepted; stops the same code being replayed.
    last_used_step = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "authenticator app"


class BackupCode(models.Model):
    """Single-use recovery code for two-factor sign-in. Only a keyed hash is stored."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="backup_codes")
    code_hash = models.CharField(max_length=64)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["user", "code_hash"], name="accounts_backup_lookup_idx")]
