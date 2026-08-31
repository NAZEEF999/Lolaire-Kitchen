"""
Django admin registrations for the tables app, using Django Unfold's
ModelAdmin as the base class per the project's DJANGO ADMIN rules.

No prepopulated_fields: Table has no slug field, so it doesn't apply.
Hard delete is disabled to enforce the project's "prefer soft
deletion" rule — deactivating is done by unchecking is_active, not
deleting the row.
"""

from django.contrib import admin
from django.contrib.admin import ModelAdmin

from core.admin_mixins import ModulePermissionAdminMixin

from .models import Table


@admin.register(Table)
class TableAdmin(ModulePermissionAdminMixin, ModelAdmin):
    lolaire_module = "tables"
    list_display = ("table_number", "name", "capacity", "status", "location", "is_active")
    list_filter = ("status", "is_active", "location")
    # "=" prefix on table_number: Django admin search requires an exact-match
    # lookup prefix for non-text fields (icontains isn't valid on an IntegerField).
    search_fields = ("=table_number", "name", "location")
    ordering = ("table_number",)
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return Table.all_objects.all()

    def has_delete_permission(self, request, obj=None):
        return False
