"""
Django admin registrations for the orders app, using Django Unfold's
ModelAdmin/TabularInline as the base classes.

order_number/subtotal/total_amount are editable=False on the model
(system-computed), so they're listed in readonly_fields purely so
they're still visible on the change form.

Hard delete is disabled on both models to enforce the project's
"prefer soft deletion" rule.
"""

from django.contrib import admin
from django.contrib.admin import ModelAdmin, TabularInline

from core.admin_mixins import ModulePermissionAdminMixin

from .models import Order, OrderItem


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    fields = ("menu_item", "quantity", "unit_price", "line_total", "notes")
    readonly_fields = ("unit_price", "line_total")
    autocomplete_fields = ["menu_item"]

    def has_delete_permission(self, request, obj=None):
        # Inline delete permission is checked independently of
        # OrderItemAdmin's — without this, the inline's delete
        # checkbox would hard-delete order items directly, bypassing
        # both the "no hard delete" policy and the served-order
        # business rule enforced in services.remove_order_item().
        return False


@admin.register(Order)
class OrderAdmin(ModulePermissionAdminMixin, ModelAdmin):
    lolaire_module = "orders"
    list_display = ("order_number", "customer", "table", "status", "payment_status", "total_amount", "created_at")
    list_filter = ("status", "payment_status", "payment_method", "is_active")
    search_fields = ("order_number", "customer__full_name", "customer__phone_number")
    ordering = ("-created_at",)
    readonly_fields = ("order_number", "subtotal", "total_amount", "created_at", "updated_at")
    autocomplete_fields = ["customer", "table"]
    inlines = [OrderItemInline]

    # Order doubles as this project's payment record (payment_status /
    # payment_method live here, there's no separate Payment model), so
    # having "Orders" access doesn't automatically mean seeing payment
    # data — that's still gated by the "payments" module specifically,
    # per the Staff Access rule that Payments gets extra protection.
    _payment_fields = {"payment_status", "payment_method", "total_amount", "subtotal"}

    def get_queryset(self, request):
        return Order.all_objects.select_related("customer", "table")

    def has_delete_permission(self, request, obj=None):
        return False

    def _can_see_payments(self, request):
        from accounts.permissions import has_admin_section

        return has_admin_section(request.user, "payments")

    def get_list_display(self, request):
        if self._can_see_payments(request):
            return self.list_display
        return tuple(f for f in self.list_display if f not in self._payment_fields)

    def get_list_filter(self, request):
        if self._can_see_payments(request):
            return self.list_filter
        return tuple(f for f in self.list_filter if f not in self._payment_fields)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if self._can_see_payments(request):
            return fields
        return [f for f in fields if f not in self._payment_fields]


@admin.register(OrderItem)
class OrderItemAdmin(ModulePermissionAdminMixin, ModelAdmin):
    lolaire_module = "orders"
    list_display = ("order", "menu_item", "quantity", "unit_price", "line_total")
    search_fields = ("order__order_number", "menu_item__name")
    ordering = ("-order__created_at",)
    readonly_fields = ("unit_price", "line_total", "created_at", "updated_at")
    autocomplete_fields = ["order", "menu_item"]

    def has_delete_permission(self, request, obj=None):
        return False
