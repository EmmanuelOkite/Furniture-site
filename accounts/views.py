from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods, require_POST

from . import sessions, throttling, tokens, twofactor
from .emails import send_account_email, send_reactivation_email
from .forms import (
    AccountPasswordChangeForm,
    AccountPasswordResetForm,
    AccountSetPasswordForm,
    ConfirmPasswordForm,
    DeleteAccountForm,
    EmailOnlyForm,
    LoginForm,
    ProfileForm,
    RegistrationForm,
    TwoFactorCodeForm,
    TwoFactorDisableForm,
)
from .models import SecurityEvent, UserSession
from .roles import DEFAULT_ROLE, get_role, set_role
from .security import logger as security_logger, record_event
from .services import LoginStatus, check_credentials, complete_login, pending_two_factor, start_two_factor

User = get_user_model()

SETUP_SECRET_SESSION_KEY = "_accounts_totp_setup_secret"


# --- Helpers -----------------------------------------------------------------


def rate_limited(request, message=None):
    response = render(
        request,
        "accounts/rate_limited.html",
        {"message": message or "Too many requests. Please wait a few minutes and try again."},
        status=429,
    )
    response["Retry-After"] = "300"
    return response


def _minutes(seconds):
    minutes = max(1, -(-seconds // 60))
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


def _safe_next(request, url):
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return url
    return None


def _confirm_password_allowed(request):
    """Re-entering the password is throttled per account so it can’t be brute-forced from a session."""
    return throttling.hit("confirm_password:id", request.user.pk)


# --- Registration -------------------------------------------------------------


@sensitive_post_parameters("password1", "password2")
@never_cache
@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST":
        if not throttling.allow(request, "register"):
            return rate_limited(request)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        email=data["email"],
                        password=data["password1"],
                        first_name=data["first_name"],
                        last_name=data["last_name"],
                        phone_number=data["phone_number"],
                    )
                    set_role(user, DEFAULT_ROLE)
            except IntegrityError:  # registered by a parallel request
                form.add_error("email", RegistrationForm.DUPLICATE_EMAIL_ERROR)
            else:
                # No email verification: the account can be used straight away.
                record_event(SecurityEvent.Type.REGISTERED, request, user=user)
                messages.success(request, "Your account has been created. Please sign in.")
                return redirect("accounts:login")

    return render(request, "accounts/register.html", {"form": form})


# --- Sign in / sign out --------------------------------------------------------


@sensitive_post_parameters("password")
@csrf_protect
@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):
    next_url = _safe_next(request, request.POST.get("next") or request.GET.get("next"))
    if request.user.is_authenticated:
        if next_url:
            # Signed in but sent here by a page they can't open (e.g. the admin).
            messages.info(request, "Your account doesn’t have access to that page.")
        return redirect("accounts:profile")

    form = LoginForm(request.POST or None)
    status = 200
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        result = check_credentials(request, data["email"], data["password"])

        if result.status is LoginStatus.OK:
            complete_login(request, result.user, remember=data["remember_me"])
            return redirect(next_url or settings.LOGIN_REDIRECT_URL)
        if result.status is LoginStatus.TWO_FACTOR_REQUIRED:
            start_two_factor(request, result.user, data["remember_me"], next_url)
            return redirect("accounts:login_two_factor")
        if result.status is LoginStatus.LOCKED:
            form.add_error(None, f"Too many sign-in attempts. Please wait {_minutes(result.retry_after)} and try again, or reset your password.")
            status = 429
        else:
            form.add_error(None, "Email or password is incorrect.")
            status = 400

    return render(
        request, "accounts/login.html", {"form": form, "next": next_url or ""}, status=status
    )


@never_cache
@require_http_methods(["GET", "POST"])
def login_two_factor(request):
    pending = pending_two_factor(request)
    if pending is None:
        messages.info(request, "Your sign-in timed out. Please sign in again.")
        return redirect("accounts:login")
    user = User.objects.filter(pk=pending["user_id"], is_active=True).first()
    if user is None:
        return redirect("accounts:login")

    form = TwoFactorCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not throttling.allow(request, "two_factor", user.pk):
            request.session.flush()
            messages.error(request, "Too many wrong codes. Please sign in again in a few minutes.")
            return redirect("accounts:login")
        method = twofactor.verify(user, form.cleaned_data["code"])
        if method:
            if method == "backup":
                record_event(SecurityEvent.Type.BACKUP_CODE_USED, request, user=user)
                left = twofactor.remaining_backup_codes(user)
                messages.warning(request, f"You used a backup code. {left} left; create new ones on your Security page if you’re running low.")
            complete_login(request, user, remember=pending["remember"], backend=pending["backend"])
            return redirect(_safe_next(request, pending["next"]) or settings.LOGIN_REDIRECT_URL)
        record_event(SecurityEvent.Type.TWO_FACTOR_FAILED, request, user=user)
        form.add_error("code", "That code isn’t valid. Check your app and try again.")

    return render(request, "accounts/login_two_factor.html", {"form": form})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        record_event(SecurityEvent.Type.LOGOUT, request, user=request.user)
        UserSession.objects.filter(session_key=request.session.session_key).delete()
    logout(request)  # flushes the session data and cookie
    messages.success(request, "You have been signed out.")
    return redirect(settings.LOGOUT_REDIRECT_URL)


# --- Passwords -------------------------------------------------------------------


@method_decorator(login_required, name="dispatch")
class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "accounts/password_change_form.html"
    form_class = AccountPasswordChangeForm
    success_url = reverse_lazy("accounts:security")

    def form_valid(self, form):
        old_key = self.request.session.session_key
        response = super().form_valid(form)  # saves and keeps this session signed in
        sessions.rekey(old_key, self.request)
        ended = sessions.revoke_all(self.request.user, except_key=self.request.session.session_key)
        record_event(SecurityEvent.Type.PASSWORD_CHANGED, self.request, user=self.request.user, other_sessions_ended=ended)
        send_account_email(self.request.user, "password_changed", self.request)
        messages.success(self.request, "Your password has been changed and you’ve been signed out on other devices.")
        return response


class PasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    form_class = AccountPasswordResetForm
    email_template_name = "accounts/emails/password_reset_body.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")
    extra_email_context = {"site_name": settings.ACCOUNTS_SITE_NAME, "timeout_minutes": settings.PASSWORD_RESET_TIMEOUT // 60}

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        identifier = form.cleaned_data["email"] if form.is_valid() else None
        if not throttling.allow(request, "password_reset", identifier):
            return rate_limited(request)
        return super().post(request, *args, **kwargs)


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """Django's view: the token is moved from the URL into the session before the form is shown."""

    template_name = "accounts/password_reset_confirm.html"
    form_class = AccountSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")
    post_reset_login = False

    def form_valid(self, form):
        response = super().form_valid(form)  # saves the password; the token is now spent
        user = form.user
        if not user.is_email_verified:
            # Following the emailed link proves they own the address; recorded for the admin.
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified_at", "updated_at"])
        sessions.revoke_all(user)
        throttling.clear_failures(user.email)
        record_event(SecurityEvent.Type.PASSWORD_RESET, self.request, user=user)
        send_account_email(user, "password_changed", self.request)
        return response


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


# --- Profile ------------------------------------------------------------------------


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def profile(request):
    # Always the signed-in user: no user id ever comes from the request.
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        if form.has_changed():
            form.save()
            record_event(SecurityEvent.Type.PROFILE_UPDATED, request, user=request.user, fields=form.changed_data)
            messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile")
    return render(
        request,
        "accounts/profile.html",
        {"form": form, "role": get_role(request.user)},
        status=400 if form.errors else 200,
    )


# --- Security settings -----------------------------------------------------------------


@login_required
@never_cache
def security(request):
    context = {
        "sessions": sessions.active_sessions(request.user),
        "current_session_key": request.session.session_key,
        "events": SecurityEvent.objects.filter(user=request.user)[:15],
        "two_factor_enabled": twofactor.is_enabled(request.user),
        "backup_codes_left": twofactor.remaining_backup_codes(request.user),
    }
    return render(request, "accounts/security.html", context)


@login_required
@require_POST
def revoke_session(request, pk):
    # Filtering by the signed-in user means another user's session id gives a 404.
    user_session = get_object_or_404(UserSession, pk=pk, user=request.user)
    if user_session.session_key == request.session.session_key:
        messages.info(request, "To end this session, use Sign out.")
        return redirect("accounts:security")
    sessions.revoke(user_session)
    record_event(SecurityEvent.Type.SESSION_REVOKED, request, user=request.user, count=1)
    messages.success(request, "That device has been signed out.")
    return redirect("accounts:security")


@login_required
@require_POST
def revoke_other_sessions(request):
    count = sessions.revoke_all(request.user, except_key=request.session.session_key)
    record_event(SecurityEvent.Type.SESSION_REVOKED, request, user=request.user, count=count)
    messages.success(request, f"Signed out of {count} other session{'s' if count != 1 else ''}.")
    return redirect("accounts:security")


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def two_factor_setup(request):
    if twofactor.is_enabled(request.user):
        return redirect("accounts:security")
    secret = request.session.get(SETUP_SECRET_SESSION_KEY)
    if not secret:
        secret = request.session[SETUP_SECRET_SESSION_KEY] = twofactor.new_secret()

    form = TwoFactorCodeForm(request.POST or None)
    form.fields["code"].help_text = "Enter the 6-digit code your app shows after scanning."
    if request.method == "POST" and form.is_valid():
        if not throttling.allow(request, "two_factor", request.user.pk):
            return rate_limited(request)
        if twofactor.match_totp(secret, form.cleaned_data["code"]) is not None:
            codes = twofactor.enable(request.user, secret)
            del request.session[SETUP_SECRET_SESSION_KEY]
            record_event(SecurityEvent.Type.TWO_FACTOR_ENABLED, request, user=request.user)
            send_account_email(request.user, "two_factor_changed", request, enabled=True)
            return render(request, "accounts/two_factor_backup_codes.html", {"codes": codes, "just_enabled": True})
        form.add_error("code", "That code isn’t valid. Check the time on your phone is correct and try again.")

    uri = twofactor.provisioning_uri(request.user, secret)
    return render(
        request,
        "accounts/two_factor_setup.html",
        {"form": form, "qr_code": twofactor.qr_code_data_uri(uri), "secret": secret},
    )


@sensitive_post_parameters("password", "code")
@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def two_factor_disable(request):
    if not twofactor.is_enabled(request.user):
        return redirect("accounts:security")
    form = TwoFactorDisableForm(request.user, request.POST or None)
    if request.method == "POST":
        if not _confirm_password_allowed(request):
            return rate_limited(request)
        if form.is_valid():
            if twofactor.verify(request.user, form.cleaned_data["code"]):
                twofactor.disable(request.user)
                record_event(SecurityEvent.Type.TWO_FACTOR_DISABLED, request, user=request.user)
                send_account_email(request.user, "two_factor_changed", request, enabled=False)
                messages.success(request, "Two-factor authentication is now off.")
                return redirect("accounts:security")
            form.add_error("code", "That code isn’t valid.")
    return render(request, "accounts/two_factor_disable.html", {"form": form})


@sensitive_post_parameters("password")
@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def two_factor_backup_codes(request):
    if not twofactor.is_enabled(request.user):
        return redirect("accounts:security")
    form = ConfirmPasswordForm(request.user, request.POST or None)
    if request.method == "POST":
        if not _confirm_password_allowed(request):
            return rate_limited(request)
        if form.is_valid():
            codes = twofactor.generate_backup_codes(request.user)
            record_event(SecurityEvent.Type.BACKUP_CODES_REGENERATED, request, user=request.user)
            return render(request, "accounts/two_factor_backup_codes.html", {"codes": codes})
    return render(request, "accounts/two_factor_regenerate.html", {"form": form})


# --- Deactivation, reactivation and deletion -------------------------------------------------


@sensitive_post_parameters("password")
@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def deactivate(request):
    form = ConfirmPasswordForm(request.user, request.POST or None)
    if request.method == "POST":
        if not _confirm_password_allowed(request):
            return rate_limited(request)
        if form.is_valid():
            user = request.user
            user.is_active = False
            user.deactivated_at = timezone.now()
            user.deactivation_reason = User.DeactivationReason.SELF
            user.save(update_fields=["is_active", "deactivated_at", "deactivation_reason", "updated_at"])
            record_event(SecurityEvent.Type.DEACTIVATED, request, user=user)
            sessions.revoke_all(user)
            logout(request)
            send_account_email(user, "deactivated", request)
            messages.success(request, "Your account has been deactivated. You can reactivate it from the sign-in page.")
            return redirect("home")
    return render(request, "accounts/deactivate.html", {"form": form})


@never_cache
@require_http_methods(["GET", "POST"])
def reactivate_request(request):
    form = EmailOnlyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        if not throttling.allow(request, "reactivate", email):
            return rate_limited(request)
        # Only accounts the owner deactivated themselves; admin suspensions stay in place.
        user = User.objects.filter(
            email=email, is_active=False, deactivation_reason=User.DeactivationReason.SELF
        ).first()
        if user is not None:
            send_reactivation_email(user, request)
        return render(request, "accounts/reactivate_sent.html")
    return render(request, "accounts/reactivate_request.html", {"form": form})


@never_cache
@require_http_methods(["GET", "POST"])
def reactivate_confirm(request, token):
    # GET only shows a button, so link scanners in mail clients can't reactivate the account.
    result = tokens.check_token(token, tokens.REACTIVATE)
    user = result.user
    if not result.valid or user.is_active or user.deactivation_reason != User.DeactivationReason.SELF:
        return render(request, "accounts/reactivate_invalid.html", {"expired": result.expired}, status=400)
    if request.method == "POST":
        user.is_active = True
        user.deactivated_at = None
        user.deactivation_reason = ""
        user.save(update_fields=["is_active", "deactivated_at", "deactivation_reason", "updated_at"])
        record_event(SecurityEvent.Type.REACTIVATED, request, user=user)
        messages.success(request, "Welcome back! Your account is active again. Please sign in.")
        return redirect("accounts:login")
    return render(request, "accounts/reactivate_confirm.html")


@sensitive_post_parameters("password")
@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def delete_account(request):
    if request.user.is_superuser:
        raise PermissionDenied("Superuser accounts can only be removed by another superuser in the admin.")
    form = DeleteAccountForm(request.user, request.POST or None)
    if request.method == "POST":
        if not _confirm_password_allowed(request):
            return rate_limited(request)
        if form.is_valid():
            user = request.user
            sessions.revoke_all(user)
            logout(request)
            send_account_email(user, "deleted", request)
            # Deleting the user also removes their audit events, sessions and 2FA data (GDPR erasure),
            # so the deletion itself goes to the security log only, by id.
            security_logger.info("account_deleted user_id=%s", user.pk)
            user.delete()
            messages.success(request, "Your account and personal data have been deleted.")
            return redirect("home")
    return render(request, "accounts/delete_account.html", {"form": form})


def admin_login_redirect(request):
    """Send the admin's sign-in through the throttled, 2FA-aware account sign-in."""
    query = request.GET.urlencode()
    return redirect(f"{reverse('accounts:login')}{'?' + query if query else ''}")
