"""
Views for the accounts app.

Authentication views subclass Django's built-in class-based auth views
rather than reimplementing login/session/token handling from scratch.
Business logic (profile updates) goes through services.py; views stay
lightweight per the project's BUSINESS LOGIC rule.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST

from . import services
from .forms import (
    AdminRecoveryIdentifyForm,
    AdminRecoveryVerifyForm,
    ProfileUpdateForm,
    StaffLoginForm,
    StaffPasswordChangeForm,
    StaffPasswordResetForm,
    StaffSetPasswordForm,
    TOTPCodeForm,
)
from .permissions import has_admin_panel_access, has_dashboard_access

User = get_user_model()
main_administrator_required = user_passes_test(lambda u: u.is_superuser, login_url="accounts:no_access")


class StaffLoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    form_class = StaffLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to

        user = self.request.user
        if has_dashboard_access(user):
            return reverse("dashboard:home")
        if has_admin_panel_access(user):
            return reverse("admin:index")
        return reverse("accounts:no_access")


@login_required
def no_access_view(request):
    """
    Where a staff member lands after logging in if they have neither
    Dashboard nor Admin Panel access yet. Not an error page — just an
    honest "nothing's turned on for you yet, ask the administrator"
    screen, so they're never stuck on a blank permission-denied response
    right after successfully logging in.
    """
    return render(request, "accounts/no_access.html")


class StaffLogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("accounts:login")


@login_required
def profile_view(request):
    """View and edit the logged-in user's own profile."""
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            services.update_profile(
                user=request.user,
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                email=form.cleaned_data["email"],
                phone_number=form.cleaned_data["phone_number"],
            )
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, "accounts/profile.html", {"form": form})


class StaffPasswordChangeView(auth_views.PasswordChangeView):
    """Login is already enforced by Django's PasswordChangeView base class."""

    template_name = "accounts/change_password.html"
    form_class = StaffPasswordChangeForm
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        messages.success(self.request, "Password changed successfully.")
        return super().form_valid(form)


class StaffPasswordResetView(auth_views.PasswordResetView):
    """
    Requests a password reset. No real email provider is wired up yet
    — EMAIL_BACKEND is set to Django's console backend, so the reset
    link is printed to the server console instead of being emailed.
    """

    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    form_class = StaffPasswordResetForm
    success_url = reverse_lazy("accounts:password_reset_done")


class StaffPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class StaffPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """
    Sets the new password (Django's own token/session handling, unchanged),
    then hands off to accounts.services.complete_password_reset — this is
    the one place that decides what happens to login access next; see
    that function's docstring for the full state machine.
    """

    template_name = "accounts/password_reset_confirm.html"
    form_class = StaffSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")

    def form_valid(self, form):
        response = super().form_valid(form)
        services.complete_password_reset(user=form.user)
        if form.user.is_superuser:
            messages.success(self.request, "Password changed successfully. You can now log in.")
        else:
            messages.success(
                self.request,
                "Password changed successfully. Your account is awaiting administrator approval before you can log in.",
            )
        return response


class StaffPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


# ── Main Administrator 2FA setup (logged-in only) ───────────────────────────
# These live in accounts/ rather than dashboard/ because they're pure
# authentication/security machinery, same reasoning as the rest of this
# file — but are still main_administrator_required, exactly like the
# dashboard.staff_security screen they're linked from.


@main_administrator_required
def totp_setup(request):
    """
    Shows current 2FA status. If not yet enabled, offers a "Generate
    a setup key" action producing a manual-entry secret (see
    accounts.totp — no QR image is generated, so nothing here makes an
    external network call or needs a new dependency; any standard
    authenticator app accepts a manual key the same way it accepts a
    scanned QR code) and the confirmation form.
    """
    user = request.user
    if request.method == "POST" and request.POST.get("intent") == "generate":
        services.begin_totp_setup(user)
        messages.info(request, "Setup key generated. Add it to your authenticator app, then enter the 6-digit code it shows to finish.")
        return redirect("accounts:totp_setup")

    confirm_form = TOTPCodeForm()
    return render(
        request,
        "accounts/totp_setup.html",
        {
            "totp_enabled": user.totp_enabled,
            "pending_secret": user.totp_secret if not user.totp_enabled else "",
            "confirm_form": confirm_form,
        },
    )


@main_administrator_required
@require_POST
def totp_setup_confirm(request):
    user = request.user
    if services.is_totp_rate_limited(user):
        messages.error(request, "Too many failed attempts. Please wait 15 minutes before trying again.")
        return redirect("accounts:totp_setup")

    form = TOTPCodeForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter the 6-digit code exactly as shown in your authenticator app.")
        return redirect("accounts:totp_setup")

    backup_codes = services.confirm_totp_setup(user=user, code=form.cleaned_data["code"])
    if backup_codes is None:
        services.record_totp_failure(user)
        messages.error(request, "That code didn't match. Generate a new setup key and try again.")
        return redirect("accounts:totp_setup")

    services.clear_totp_rate_limit(user)
    return render(request, "accounts/totp_backup_codes.html", {"backup_codes": backup_codes, "regenerated": False})


@main_administrator_required
@require_POST
def totp_backup_codes_regenerate(request):
    """
    Invalidates every existing backup code (used or not) and issues a
    fresh set — for when the Main Administrator has used most of them,
    or suspects an old set may have leaked.
    """
    backup_codes = services.regenerate_backup_codes(request.user)
    messages.success(request, "New backup codes generated. Your previous codes no longer work.")
    return render(request, "accounts/totp_backup_codes.html", {"backup_codes": backup_codes, "regenerated": True})


# ── Main Administrator account recovery (logged-out, TOTP-verified) ────────
# Deliberately a separate, self-contained flow rather than a branch
# inside StaffPasswordResetView above: that view's token/email
# machinery comes straight from Django's own PasswordResetConfirmView
# internals, and bending it to also demand a TOTP step risked subtly
# breaking the parts of it this project didn't need to touch. Three
# plain steps, state carried in the session between them:
#   1. identify(username/email)   -> session["admin_recovery_uid"]
#   2. verify(TOTP or backup code) -> session["admin_recovery_verified_uid"]
#   3. set new password            -> session keys cleared either way


ADMIN_RECOVERY_GENERIC_MESSAGE = (
    "If that identifies a Main Administrator account with two-factor authentication set up, "
    "you'll be asked to verify with your authenticator app next."
)


def admin_recovery_identify(request):
    if request.method == "POST":
        form = AdminRecoveryIdentifyForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data["username"]
            candidate = User.objects.filter(is_superuser=True).filter(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            ).first()
            if candidate is not None and candidate.totp_enabled:
                request.session["admin_recovery_uid"] = candidate.pk
                return redirect("accounts:admin_recovery_verify")
            messages.info(request, ADMIN_RECOVERY_GENERIC_MESSAGE)
            return redirect("accounts:admin_recovery_identify")
    else:
        form = AdminRecoveryIdentifyForm()

    return render(request, "accounts/admin_recovery_identify.html", {"form": form})


def admin_recovery_verify(request):
    uid = request.session.get("admin_recovery_uid")
    if not uid:
        return redirect("accounts:admin_recovery_identify")
    user = User.objects.filter(pk=uid, is_superuser=True, totp_enabled=True).first()
    if user is None:
        request.session.pop("admin_recovery_uid", None)
        return redirect("accounts:admin_recovery_identify")

    if request.method == "POST":
        if services.is_totp_rate_limited(user):
            messages.error(request, "Too many failed attempts. Please wait 15 minutes before trying again.")
            return render(request, "accounts/admin_recovery_verify.html", {"form": AdminRecoveryVerifyForm()})

        form = AdminRecoveryVerifyForm(request.POST)
        if form.is_valid() and services.verify_totp_or_backup_code(user=user, code=form.cleaned_data["code"]):
            services.clear_totp_rate_limit(user)
            request.session.pop("admin_recovery_uid", None)
            request.session["admin_recovery_verified_uid"] = user.pk
            return redirect("accounts:admin_recovery_set_password")
        services.record_totp_failure(user)
        messages.error(request, "That code didn't verify. Check your authenticator app and try again.")
    else:
        form = AdminRecoveryVerifyForm()

    return render(request, "accounts/admin_recovery_verify.html", {"form": form})


def admin_recovery_set_password(request):
    uid = request.session.get("admin_recovery_verified_uid")
    if not uid:
        return redirect("accounts:admin_recovery_identify")
    user = User.objects.filter(pk=uid, is_superuser=True).first()
    if user is None:
        request.session.pop("admin_recovery_verified_uid", None)
        return redirect("accounts:admin_recovery_identify")

    if request.method == "POST":
        form = StaffSetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            request.session.pop("admin_recovery_verified_uid", None)
            messages.success(request, "Password changed successfully. You can now log in.")
            return redirect("accounts:login")
    else:
        form = StaffSetPasswordForm(user)

    return render(request, "accounts/admin_recovery_set_password.html", {"form": form})

