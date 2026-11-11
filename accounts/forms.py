from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError

from .validators import normalize_email_address

User = get_user_model()

PASSWORD_HELP = password_validation.password_validators_help_text_html


def _email_field(**attrs):
    return forms.EmailField(
        label="Email address",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email", **attrs}),
    )


def _new_password_widget():
    # data-strength-meter: the client-side meter is a hint only; the server validates.
    return forms.PasswordInput(attrs={"autocomplete": "new-password", "data-strength-meter": ""})


def _confirm_widget(match_id):
    return forms.PasswordInput(attrs={"autocomplete": "new-password", "data-match": match_id})


class RegistrationForm(forms.Form):
    """
    Sign-up form. A plain Form, not a ModelForm: the view decides exactly which
    fields reach the model (no mass assignment).
    """

    DUPLICATE_EMAIL_ERROR = "An account with this email address already exists. Sign in or reset your password."

    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"autocomplete": "given-name"}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"autocomplete": "family-name"}))
    email = _email_field()
    phone_number = forms.CharField(
        label="Phone number",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
        validators=User._meta.get_field("phone_number").validators,
    )
    password1 = forms.CharField(label="Password", strip=False, widget=_new_password_widget(), help_text=PASSWORD_HELP)
    password2 = forms.CharField(label="Confirm password", strip=False, widget=_confirm_widget("id_password1"))

    def clean_first_name(self):
        return self.cleaned_data["first_name"].strip()

    def clean_last_name(self):
        return self.cleaned_data["last_name"].strip()

    def clean_email(self):
        email = normalize_email_address(self.cleaned_data["email"])
        if User._default_manager.filter(email=email).exists():
            raise ValidationError(self.DUPLICATE_EMAIL_ERROR, code="duplicate_email")
        return email

    def clean_phone_number(self):
        return self.cleaned_data["phone_number"].strip()

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", ValidationError("The two passwords don’t match.", code="password_mismatch"))
        if p1:
            # Compare against what the user typed (name, email) to reject guessable passwords.
            candidate = User(
                email=cleaned.get("email", ""),
                first_name=cleaned.get("first_name", ""),
                last_name=cleaned.get("last_name", ""),
            )
            try:
                password_validation.validate_password(p1, candidate)
            except ValidationError as error:
                self.add_error("password1", error)
        return cleaned


class LoginForm(forms.Form):
    email = _email_field(autofocus=True)
    password = forms.CharField(
        strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"})
    )
    remember_me = forms.BooleanField(label="Keep me signed in on this device", required=False)


class TwoFactorCodeForm(forms.Form):
    code = forms.CharField(
        label="Authentication code",
        max_length=20,
        help_text="The 6-digit code from your authenticator app, or one of your backup codes.",
        widget=forms.TextInput(
            attrs={"autocomplete": "one-time-code", "inputmode": "numeric", "autofocus": True, "spellcheck": "false"}
        ),
    )


class EmailOnlyForm(forms.Form):
    email = _email_field(autofocus=True)

    def clean_email(self):
        return normalize_email_address(self.cleaned_data["email"])


class ProfileForm(forms.ModelForm):
    """Only these fields can be changed by the account holder; role, email and status cannot."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone_number"]
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "phone_number": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
        }

    def clean_first_name(self):
        return self.cleaned_data["first_name"].strip()

    def clean_last_name(self):
        return self.cleaned_data["last_name"].strip()


class ConfirmPasswordForm(forms.Form):
    """Re-enter the current password before a sensitive change."""

    password = forms.CharField(
        label="Current password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise ValidationError("Your password is incorrect.", code="password_incorrect")
        return password


class DeleteAccountForm(ConfirmPasswordForm):
    confirm = forms.CharField(
        label="Type DELETE to confirm",
        max_length=10,
        widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
    )

    def clean_confirm(self):
        if self.cleaned_data["confirm"].strip() != "DELETE":
            raise ValidationError("Type DELETE in capital letters to confirm.", code="confirm_mismatch")
        return "DELETE"


class TwoFactorDisableForm(ConfirmPasswordForm):
    code = TwoFactorCodeForm.base_fields["code"]


class AccountPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget = _new_password_widget()
        self.fields["new_password2"].widget = _confirm_widget("id_new_password1")
        self.fields["old_password"].widget.attrs.pop("autofocus", None)


class AccountSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget = _new_password_widget()
        self.fields["new_password2"].widget = _confirm_widget("id_new_password1")


class AccountPasswordResetForm(PasswordResetForm):
    email = _email_field(autofocus=True)

    def clean_email(self):
        return normalize_email_address(self.cleaned_data["email"])
