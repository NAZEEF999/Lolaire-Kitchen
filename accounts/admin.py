"""
Django admin registrations for the accounts app, using Django Unfold's
ModelAdmin as the base class per the project's DJANGO ADMIN rules.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.admin import ModelAdmin

from core.admin_mixins import SuperuserOnlyAdminMixin

from .forms import StaffChangeForm, StaffCreationForm
from .models import StaffAccess, User


@admin.register(User)
class UserAdmin(SuperuserOnlyAdminMixin, BaseUserAdmin, ModelAdmin):
    """
    Admin for staff accounts — Main Administrator only, full stop,
    regardless of any StaffAccess toggle (see SuperuserOnlyAdminMixin's
    docstring for why). This screen exposes is_superuser, is_staff,
    groups, and user_permissions directly; the Dashboard's Staff
    Management pages are the intended day-to-day interface for
    everyone else and never expose those fields at all.
    """

    form = StaffChangeForm
    add_form = StaffCreationForm

    list_display = ("username", "display_full_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email", "phone_number")
    ordering = ("username",)
    readonly_fields = ("last_login", "date_joined", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "email", "phone_number")},
        ),
        (
            "Role & permissions",
            {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        (
            "Important dates",
            {"fields": ("last_login", "date_joined", "created_at", "updated_at")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "role", "password1", "password2"),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        """Prevents the Main Administrator from accidentally stripping their own is_superuser/is_active here — the same self-lockout protection accounts.services enforces for the Dashboard's Activate/Deactivate action."""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.pk == request.user.pk:
            readonly += ["is_superuser", "is_active"]
        return readonly

    @admin.display(description="Full name")
    def display_full_name(self, obj):
        return obj.get_full_name() or "—"


@admin.register(StaffAccess)
class StaffAccessAdmin(SuperuserOnlyAdminMixin, ModelAdmin):
    """
    Raw view of the Staff Access rows — Main Administrator only (see
    SuperuserOnlyAdminMixin). Day-to-day permission changes should go
    through the friendlier toggle UI in the Dashboard (Staff → Manage
    Access) — this is just for visibility/debugging, and must never be
    reachable by the staff members it's describing.
    """

    list_display = ("user", "dashboard_enabled", "admin_panel_enabled", "nav_dashboard_to_admin", "nav_admin_to_dashboard")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "updated_at")
