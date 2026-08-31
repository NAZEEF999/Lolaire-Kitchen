"""
Django admin registrations for the menu app, using Django Unfold's
ModelAdmin as the base class per the project's DJANGO ADMIN rules.

Both admins expose all_objects (including soft-deleted rows) so staff
can review and reactivate deactivated categories/items, and both
disable the built-in hard-delete action to enforce the project's
"prefer soft deletion" rule — deactivating is done by unchecking
is_active, not by deleting the row.
"""

from django.contrib import admin
from django.contrib.admin import ModelAdmin

from core.admin_mixins import ModulePermissionAdminMixin

from .models import Category, MenuItem


@admin.register(Category)
class CategoryAdmin(ModulePermissionAdminMixin, ModelAdmin):
    lolaire_module = "menu"
    list_display = ("name", "slug", "display_order", "is_active", "item_count")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    ordering = ("display_order", "name")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return Category.all_objects.all()

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Items")
    def item_count(self, obj):
        return obj.menu_items.count()


@admin.register(MenuItem)
class MenuItemAdmin(ModulePermissionAdminMixin, ModelAdmin):
    lolaire_module = "menu"
    list_display = ("name", "category", "price", "is_available", "is_featured", "is_active")
    list_filter = ("category", "is_available", "is_featured", "is_active")
    search_fields = ("name", "description", "category__name")
    ordering = ("category__display_order", "name")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ["category"]
    list_editable = ("is_featured",)

    def get_queryset(self, request):
        return MenuItem.all_objects.select_related("category")

    def has_delete_permission(self, request, obj=None):
        return False
