"""Django admin registrations for the inventory app."""

from django.contrib import admin
from django.contrib.admin import ModelAdmin

from core.admin_mixins import ModulePermissionAdminMixin

from .models import Ingredient, StockAdjustment, Supplier


@admin.register(Supplier)
class SupplierAdmin(ModulePermissionAdminMixin, ModelAdmin):
    lolaire_module = "inventory"
    list_display = ("name", "contact_name", "phone_number", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "contact_name", "phone_number", "email")


@admin.register(Ingredient)
class IngredientAdmin(ModulePermissionAdminMixin, ModelAdmin):
    lolaire_module = "inventory"
    list_display = ("name", "unit", "quantity_in_stock", "low_stock_threshold", "supplier", "is_active")
    list_filter = ("unit", "is_active", "supplier")
    search_fields = ("name",)
    readonly_fields = ("quantity_in_stock",)  # Changed only via StockAdjustment — see inventory.services.record_stock_adjustment.


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(ModulePermissionAdminMixin, ModelAdmin):
    lolaire_module = "inventory"
    list_display = ("ingredient", "reason", "quantity_delta", "adjusted_by", "created_at")
    list_filter = ("reason",)
    search_fields = ("ingredient__name", "note")
    readonly_fields = ("ingredient", "reason", "quantity_delta", "note", "adjusted_by", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False  # Only created through inventory.services.record_stock_adjustment, never directly.

    def has_change_permission(self, request, obj=None):
        return False  # Immutable history — corrections are their own new adjustment, not an edit of the old one.
