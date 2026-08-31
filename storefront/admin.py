"""Django admin registration for the storefront app."""

from django.contrib import admin

from core.admin_mixins import ModulePermissionAdminMixin

from .models import ContactMessage, Review


@admin.register(ContactMessage)
class ContactMessageAdmin(ModulePermissionAdminMixin, admin.ModelAdmin):
    lolaire_module = "customers"  # Contact messages are customer-facing correspondence, closest existing module.
    list_display = ("full_name", "email", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("full_name", "email", "message")
    readonly_fields = ("full_name", "email", "message", "created_at", "updated_at")
    list_editable = ("is_read",)

    def has_add_permission(self, request):
        return False  # Only created through the public contact form.


@admin.register(Review)
class ReviewAdmin(ModulePermissionAdminMixin, admin.ModelAdmin):
    lolaire_module = "customers"  # Same reasoning as ContactMessage — public customer feedback, not its own StaffAccess module.
    list_display = ("full_name", "rating", "is_approved", "is_featured", "created_at")
    list_filter = ("rating", "is_approved", "is_featured", "created_at")
    search_fields = ("full_name", "email", "review")
    readonly_fields = ("full_name", "email", "rating", "review", "created_at", "updated_at")
    list_editable = ("is_approved", "is_featured")

    def has_add_permission(self, request):
        return False  # Only created through the public review form.
