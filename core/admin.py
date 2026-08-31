"""
Project-wide Django admin configuration.

Per-model registrations (list_display, search_fields, list_filter,
ordering, readonly_fields) belong in each app's own admin.py, using
django.contrib.admin.ModelAdmin (with ModulePermissionAdminMixin, see
core/admin_mixins.py) as the base class. This file carries site-wide
branding plus the top-level "can this user open /admin/ at all" gate.
"""

from django.contrib import admin
from unfold.sites import UnfoldAdminSite

from accounts.permissions import has_admin_panel_access

from .admin_mixins import SuperuserOnlyAdminMixin
from .models import RestaurantSettings

admin.site.site_title = "Restaurant Management System"
admin.site.site_header = "Restaurant Management System"
admin.site.index_title = "Administration"


class LolaireAdminSite(UnfoldAdminSite):
    """
    Adds the Staff Access "Admin Panel" gate on top of Django's normal
    is_active/is_staff check. A superuser always passes. A non-superuser
    staff member must additionally have admin_panel_enabled — otherwise
    every /admin/ URL, not just the index, is denied (has_permission is
    checked by Django Admin's own admin_view() wrapper on every single
    admin request).

    Subclasses Unfold's UnfoldAdminSite rather than plain Django
    AdminSite — Unfold's own chrome (the sidebar toggle button,
    included via unfold/helpers/welcomemsg.html) reverses URLs like
    "admin:toggle_sidebar" that only exist on Unfold's site class.
    Building on plain AdminSite here causes a NoReverseMatch on every
    admin page load, since those extra URLs are added by
    UnfoldAdminSite.get_urls(), not by "unfold" merely being in
    INSTALLED_APPS.
    """

    def has_permission(self, request):
        return super().has_permission(request) and has_admin_panel_access(request.user)


# Re-point the existing admin.site singleton at the new class in place,
# rather than instantiating a second AdminSite — every app's admin.py
# already registers its models on admin.site via @admin.register(...),
# so this keeps every existing registration working unchanged.
admin.site.__class__ = LolaireAdminSite


@admin.register(RestaurantSettings)
class RestaurantSettingsAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    """
    Site-wide restaurant configuration (currency, delivery fee, tax
    rate, exchange rate, etc). Not part of the StaffAccess module
    system — like the Dashboard's settings_stub, this is Main
    Administrator territory only, since it affects pricing/tax across
    the entire storefront and dashboard.
    """

    list_display = (
        "restaurant_name",
        "base_currency",
        "display_currency",
        "exchange_rate",
        "auto_update_exchange_rate",
        "is_active",
        "updated_at",
    )
    search_fields = ("restaurant_name", "phone", "email", "address")
    list_filter = ("is_active", "base_currency", "display_currency", "auto_update_exchange_rate")
    readonly_fields = ("created_at", "updated_at", "exchange_rate_updated_at")
    fieldsets = (
        ("Restaurant Information", {"fields": ("restaurant_name", "tagline", "about")}),
        ("Contact", {"fields": ("phone", "email", "address")}),
        (
            "Location",
            {
                "fields": ("latitude", "longitude"),
                "description": (
                    "Used to draw the restaurant's point on the Track Order map "
                    "and to build the \"Get Directions\" link. Look these up once on "
                    "Google Maps (right-click your location \u2192 the coordinates are "
                    "the first item in the menu) and paste them in \u2014 no API key needed."
                ),
            },
        ),
        ("Operations", {"fields": ("opening_hours", "delivery_fee", "tax_rate", "minimum_order_amount")}),
        (
            "Currency & Exchange Rate",
            {
                "fields": (
                    "base_currency",
                    "display_currency",
                    "exchange_rate_provider",
                    "exchange_rate",
                    "exchange_rate_updated_at",
                    "auto_update_exchange_rate",
                ),
                "description": (
                    "Restaurant prices remain stored in the base currency. "
                    "The display currency is used only for customer-facing price conversion."
                ),
            },
        ),
        ("Social Media", {"fields": ("instagram_url", "facebook_url", "twitter_url", "tiktok_url")}),
        ("Status", {"fields": ("is_active", "created_at", "updated_at")}),
    )