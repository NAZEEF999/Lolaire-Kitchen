"""
Makes Staff Access permission checks available in every template as
plain booleans, so the sidebar/navbar/admin templates can do simple
{% if %} checks instead of calling permission functions directly.
Reminder: this only controls what's *shown* — the real enforcement is
accounts.middleware.StaffAccessMiddleware, core.admin_mixins
.ModulePermissionAdminMixin, and each view's own action-level check
(has_dashboard_action), see those for the actual security layer.
"""

from django.urls import reverse

from . import permissions as perms


def _quick_actions(user):
    """
    Real, working destinations only — each entry here is gated by the
    exact same "create" action permission that protects the
    destination view itself, and every URL is a genuine existing page
    (see the Quick Actions summary in dashboard docs for what was
    deliberately left out and why, e.g. reservations has no staff-side
    creation view yet). "Manage Staff" checks is_superuser directly,
    not the "staff" StaffAccess module — see can_staff's note below.
    """
    actions = []
    if perms.has_dashboard_action(user, "orders", "create"):
        actions.append({"label": "New Order", "url": reverse("orders:create"), "icon": "order"})
    if perms.has_dashboard_action(user, "menu", "create"):
        actions.append({"label": "Add Menu Item", "url": reverse("menu:item_create"), "icon": "menu"})
    if perms.has_dashboard_action(user, "customers", "create"):
        actions.append({"label": "Add Customer", "url": reverse("customers:create"), "icon": "customer"})
    if perms.has_dashboard_action(user, "tables", "create"):
        actions.append({"label": "Add Table", "url": reverse("tables:create"), "icon": "table"})
    if perms.has_dashboard_action(user, "inventory", "create"):
        actions.append({"label": "Add Ingredient", "url": reverse("inventory:ingredient_create"), "icon": "inventory"})
    if user.is_superuser:
        actions.append({"label": "Manage Staff", "url": reverse("dashboard:staff_list"), "icon": "staff"})
    return actions


def staff_access(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    context = {
        "can_dashboard": perms.has_dashboard_access(user),
        "can_admin_panel": perms.has_admin_panel_access(user),
        "can_dashboard_to_admin": perms.can_navigate_dashboard_to_admin(user),
        "can_admin_to_dashboard": perms.can_navigate_admin_to_dashboard(user),
        # "module ON" alone used to be enough here, which meant a
        # sidebar link (or a template's "can I see this data" check)
        # could show for someone whose View action was actually OFF —
        # the toggle existed but did nothing. Every flag below now
        # requires the specific "view" action, not just the module.
        "can_orders": perms.has_dashboard_action(user, "orders", "view"),
        "can_reservations": perms.has_dashboard_action(user, "reservations", "view"),
        "can_customers": perms.has_dashboard_action(user, "customers", "view"),
        "can_tables": perms.has_dashboard_action(user, "tables", "view"),
        "can_menu": perms.has_dashboard_action(user, "menu", "view"),
        "can_payments": perms.has_dashboard_action(user, "payments", "view"),
        "can_reports": perms.has_dashboard_action(user, "reports", "view"),
        "can_inventory": perms.has_dashboard_action(user, "inventory", "view"),
        # Staff Management is a security-sensitive administrative
        # function, not an ordinary operational module — this is
        # is_superuser directly, never the "staff" StaffAccess module,
        # matching every Staff Management view's own
        # main_administrator_required decorator. Granting someone the
        # "staff" module (kept only for backward-compatible JSON
        # shape) must never make this True.
        "can_staff": bool(user.is_superuser),
    }

    if context["can_inventory"]:
        from inventory.selectors import get_low_stock_count

        context["low_stock_count"] = get_low_stock_count()

    if context["can_orders"]:
        from dashboard.selectors import get_pending_orders

        context["pending_orders_count"] = get_pending_orders()

    context["quick_actions"] = _quick_actions(user)

    if user.is_superuser:
        # Cheap enough to run on every page (a handful of rows, indexed
        # lookup) and only ever computed for the one Main Administrator
        # account — lets the sidebar badge stay up to date wherever
        # they are in the Dashboard, not just on the Staff Security page.
        from .models import AccountRecoveryRequest, RecoveryRequestStatus

        context["pending_recovery_count"] = AccountRecoveryRequest.objects.filter(
            status=RecoveryRequestStatus.PENDING
        ).count()

    return context
