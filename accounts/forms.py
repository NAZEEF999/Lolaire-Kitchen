"""
ModelForms for the accounts app.
"""

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserChangeForm as BaseUserChangeForm,
    UserCreationForm as BaseUserCreationForm,
)

from .models import StaffTag, User

TAILWIND_INPUT = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-blue-500"
)


class TailwindFormMixin:
    """Applies consistent Tailwind classes to every visible field widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {TAILWIND_INPUT}".strip()


# ── Site-facing forms (Tailwind-styled, used by accounts/views.py) ─────────


class StaffLoginForm(TailwindFormMixin, AuthenticationForm):
    """Login form for staff accounts."""

    def confirm_login_allowed(self, user):
        """
        Overrides Django's generic "This account is inactive." message
        with the specific reason, taken from AccountStatus — matches
        the copy the recovery flow itself uses, so staff never see two
        different explanations for the same thing. Still deliberately
        stops short of explaining *why* an account was suspended,
        which is a Main Administrator decision made outside this form.
        """
        if user.is_active:
            return
        from .models import AccountStatus

        if user.account_status == AccountStatus.RECOVERY_PENDING:
            raise forms.ValidationError(
                "Your account is awaiting administrator approval before you can log in.", code="recovery_pending"
            )
        if user.account_status == AccountStatus.RECOVERY_REJECTED:
            raise forms.ValidationError(
                "Your account recovery request was not approved. Please contact the administrator.",
                code="recovery_rejected",
            )
        if user.account_status == AccountStatus.SUSPENDED:
            raise forms.ValidationError("Your account has been suspended. Please contact the administrator.", code="suspended")
        super().confirm_login_allowed(user)


class ProfileUpdateForm(TailwindFormMixin, forms.ModelForm):
    """Lets a logged-in staff member update their own basic details."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone_number"]


class StaffPasswordChangeForm(TailwindFormMixin, PasswordChangeForm):
    """Change-password form for a logged-in user."""


class StaffPasswordResetForm(TailwindFormMixin, PasswordResetForm):
    """
    Requests a password reset. Structure only for now — no real email
    provider is wired up yet (see EMAIL_BACKEND in core/settings.py).
    """


class StaffSetPasswordForm(TailwindFormMixin, SetPasswordForm):
    """Sets a new password after a valid reset token is confirmed."""


# ── Main Administrator 2FA (TOTP) ───────────────────────────────────────────


class TOTPCodeForm(TailwindFormMixin, forms.Form):
    """A single 6-digit authenticator code — used both to confirm initial 2FA setup and (via AdminRecoveryVerifyForm below) is not reused directly for recovery since that also accepts backup codes."""

    code = forms.CharField(
        label="6-digit code",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code", "placeholder": "000000"}),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit():
            raise forms.ValidationError("Enter the 6-digit code from your authenticator app.")
        return code


class AdminRecoveryIdentifyForm(TailwindFormMixin, forms.Form):
    """Step 1 of Main Administrator recovery — just confirms who's asking, same generic response either way (see AdminRecoveryIdentifyView)."""

    username = forms.CharField(label="Username or email")


class AdminRecoveryVerifyForm(TailwindFormMixin, forms.Form):
    """Step 2 — accepts either a live 6-digit TOTP code or a backup-code (format 123456-654321), so the field isn't restricted to digits-only like TOTPCodeForm."""

    code = forms.CharField(
        label="Authenticator code or backup code",
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "placeholder": "000000 or backup code"}),
    )

    def clean_code(self):
        return self.cleaned_data["code"].strip()


# ── Staff tags ───────────────────────────────────────────────────────────


class StaffTagForm(TailwindFormMixin, forms.ModelForm):
    """Organizational label only — see StaffTag's docstring for why this is deliberately kept far away from anything permission-related."""

    class Meta:
        model = StaffTag
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "e.g. Kitchen"})}


# ── Admin-facing forms (used by accounts/admin.py; left unstyled since ─────
# ── Django Unfold applies its own styling to the admin site) ───────────────


class StaffCreationForm(BaseUserCreationForm):
    """Creates a new staff account from the Django admin."""

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("username", "role", "first_name", "last_name", "email", "phone_number")


class StaffChangeForm(BaseUserChangeForm):
    """Edits an existing staff account from the Django admin."""

    class Meta(BaseUserChangeForm.Meta):
        model = User
        fields = "__all__"
