"""
URL configuration for the accounts app.

Registered under app_name="accounts" and included from core/urls.py.
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.StaffLoginView.as_view(), name="login"),
    path("no-access/", views.no_access_view, name="no_access"),
    path("logout/", views.StaffLogoutView.as_view(), name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/change-password/", views.StaffPasswordChangeView.as_view(), name="change_password"),
    path("password-reset/", views.StaffPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", views.StaffPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", views.StaffPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", views.StaffPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    # Main Administrator 2FA setup (logged-in)
    path("security/2fa/", views.totp_setup, name="totp_setup"),
    path("security/2fa/confirm/", views.totp_setup_confirm, name="totp_setup_confirm"),
    path("security/2fa/backup-codes/regenerate/", views.totp_backup_codes_regenerate, name="totp_backup_codes_regenerate"),
    # Main Administrator account recovery (logged-out, TOTP-verified)
    path("admin-recovery/", views.admin_recovery_identify, name="admin_recovery_identify"),
    path("admin-recovery/verify/", views.admin_recovery_verify, name="admin_recovery_verify"),
    path("admin-recovery/set-password/", views.admin_recovery_set_password, name="admin_recovery_set_password"),
]
