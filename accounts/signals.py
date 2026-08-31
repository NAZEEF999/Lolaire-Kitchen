"""
Signal handlers for the accounts app.

Connected in accounts/apps.py's AccountsConfig.ready().
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import StaffAccess, User


@receiver(post_save, sender=StaffAccess)
def sync_admin_panel_staff_flag(sender, instance, **kwargs):
    """
    Keeps User.is_staff aligned with StaffAccess.admin_panel_enabled —
    is_staff is Django's own built-in flag, and Django Admin's
    AdminSite.has_permission() checks it *before* LolaireAdminSite's
    own admin_panel_enabled check even runs (see core/admin.py's
    `super().has_permission(request) and has_admin_panel_access(...)`
    — the `super()` call is exactly this is_staff check). The two
    must never contradict each other, which is what happened when
    is_staff used to be derived from the legacy `role` field instead:
    a Cashier granted Admin Panel access through StaffAccess could
    still be blocked at the door because their role wasn't
    Administrator/Manager. Superusers are left untouched here — they
    always have admin access regardless of any StaffAccess row.
    """
    user = instance.user
    if user.is_superuser:
        return
    desired = bool(instance.admin_panel_enabled)
    if user.is_staff != desired:
        User.objects.filter(pk=user.pk).update(is_staff=desired)
