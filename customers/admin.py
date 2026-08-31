"""
Django admin registrations for the customers app, using Django
Unfold's ModelAdmin as the base class per the project's DJANGO ADMIN
rules.

No prepopulated_fields: Customer has no slug field, so it doesn't apply.
Hard delete is disabled to enforce the project's "prefer soft deletion"
rule — deactivating is done by unchecking is_active, not deleting the row.
"""

from django.contrib import admin
from django.contrib.admin import ModelAdmin

from core.admin_mixins import ModulePermissionAdminMixin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(ModulePermissionAdminMixin, ModelAdmin):
    lolaire_module = "customers"
    list_display = ("full_name", "phone_number", "email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("full_name", "phone_number", "email")
    ordering = ("full_name",)
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return Customer.all_objects.all()

    def has_delete_permission(self, request, obj=None):
        return False
