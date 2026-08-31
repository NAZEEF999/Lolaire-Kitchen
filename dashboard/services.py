"""
Business logic for the dashboard app.

Assembles the raw numbers from selectors.py into the shapes views and
templates need: permission-filtered statistics and Chart.js-ready
datasets. Views stay lightweight per the project's BUSINESS LOGIC
rule.
"""

from . import selectors


def get_dashboard_statistics():
    """
    Every dashboard stat, unfiltered. Returns 0 for any figure whose
    underlying app (customers/menu/orders/tables/reservations) hasn't
    been built yet — see selectors.py for the defensive lookups behind
    this.
    """
    return {
        "total_customers": selectors.get_total_customers(),
        "new_customers_today": selectors.get_new_customers_today(),
        "total_menu_items": selectors.get_total_menu_items(),
        "total_orders": selectors.get_total_orders(),
        "todays_orders": selectors.get_todays_orders(),
        "pending_orders": selectors.get_pending_orders(),
        "completed_orders": selectors.get_completed_orders(),
        "available_tables": selectors.get_available_tables(),
        "occupied_tables": selectors.get_occupied_tables(),
        "reservations_today": selectors.get_reservations_today(),
        "pending_reservations": selectors.get_pending_reservations(),
        "daily_revenue": selectors.get_daily_revenue(),
        "weekly_revenue": selectors.get_weekly_revenue(),
        "monthly_revenue": selectors.get_monthly_revenue(),
        "cancelled_payments": selectors.get_cancelled_payments(),
        "low_stock_count": _get_low_stock_count(),
    }


def _get_low_stock_count():
    """Cross-app read, same precedent as dashboard reading Order/Reservation directly. Only guards against ImportError (the inventory app genuinely not being installed in some environment) — not a broad catch-all, since inventory is otherwise a real, stable, migrated app in this project."""
    try:
        from inventory.selectors import get_low_stock_count

        return get_low_stock_count()
    except ImportError:
        return 0


def get_statistics_for_role(role):
    """
    REMOVED — this function used to gate stat visibility by
    `role` (Administrator/Manager/Cashier/Waiter) in addition to
    StaffAccess, which meant StaffAccess was never actually the sole
    source of truth: a Waiter granted Payments through StaffAccess
    could still have revenue silently withheld here regardless. Stat
    visibility is now decided entirely by filter_stats_by_permission()
    below, which checks StaffAccess only. Kept as a stub (rather than
    deleting outright) only so any stale caller fails loudly instead
    of silently importing a name that no longer exists — remove this
    stub entirely once nothing references it anymore.
    """
    raise NotImplementedError(
        "get_statistics_for_role was removed — role no longer gates dashboard statistics. "
        "Use get_dashboard_statistics() + filter_stats_by_permission(user, stats) instead."
    )


# Which Staff Access module owns each stat — used to strip stats the
# viewer's StaffAccess doesn't permit, on top of the coarser
# role-based filter above. Keeps the "if Orders is OFF, don't show
# order statistics" rule in one place rather than repeated per-view.
STAT_MODULE_OWNER = {
    "total_customers": "customers",
    "new_customers_today": "customers",
    "total_menu_items": "menu",
    "total_orders": "orders",
    "todays_orders": "orders",
    "pending_orders": "orders",
    "completed_orders": "orders",
    "available_tables": "tables",
    "occupied_tables": "tables",
    "reservations_today": "reservations",
    "pending_reservations": "reservations",
    "daily_revenue": "payments",
    "weekly_revenue": "payments",
    "monthly_revenue": "payments",
    "cancelled_payments": "payments",
    "low_stock_count": "inventory",
}


def filter_stats_by_permission(user, stats):
    """Drops any stat whose owning module the user's StaffAccess doesn't have View turned on for — see STAT_MODULE_OWNER. Superusers always see everything, per has_dashboard_action."""
    from accounts.permissions import has_dashboard_action

    return {key: value for key, value in stats.items() if has_dashboard_action(user, STAT_MODULE_OWNER.get(key, key), "view")}


def get_revenue_chart_data():
    """Chart.js-ready dataset comparing daily/weekly/monthly revenue."""
    stats = get_dashboard_statistics()
    return {
        "labels": ["Today", "This Week", "This Month"],
        "datasets": [{
            "label": "Revenue",
            "data": [float(stats["daily_revenue"]), float(stats["weekly_revenue"]), float(stats["monthly_revenue"])],
        }],
    }


def get_orders_chart_data():
    """Chart.js-ready dataset comparing pending vs completed orders."""
    stats = get_dashboard_statistics()
    return {
        "labels": ["Pending", "Completed"],
        "datasets": [{
            "label": "Orders",
            "data": [stats["pending_orders"], stats["completed_orders"]],
        }],
    }


def get_tables_chart_data():
    """Chart.js-ready dataset comparing available vs occupied tables."""
    stats = get_dashboard_statistics()
    return {
        "labels": ["Available", "Occupied"],
        "datasets": [{
            "label": "Tables",
            "data": [stats["available_tables"], stats["occupied_tables"]],
        }],
    }


def get_popular_items_chart_data():
    """Chart.js-ready dataset of the top 5 menu items by quantity ordered."""
    rows = selectors.get_popular_menu_items(limit=5)
    return {
        "labels": [row["name"] for row in rows],
        "datasets": [{"label": "Units ordered", "data": [row["quantity"] for row in rows]}],
    }


def get_order_status_chart_data():
    """Chart.js-ready dataset of order counts grouped by status."""
    breakdown = selectors.get_order_status_breakdown()
    labels = list(breakdown.keys())
    return {
        "labels": [label.replace("_", " ").title() for label in labels],
        "datasets": [{"label": "Orders", "data": [breakdown[label] for label in labels]}],
    }


# Status → color mapping, used consistently for the Live Activity feed,
# stat cards, and status badges. GREEN = healthy/complete, AMBER =
# needs attention, RED = critical, BLUE = informational — see the
# STATUS COLORS section of static/css/custom.css for the actual classes.
ORDER_STATUS_COLOR = {"pending": "warning", "preparing": "warning", "ready": "warning", "served": "success", "cancelled": "critical"}
RESERVATION_STATUS_COLOR = {"pending": "warning", "confirmed": "success", "completed": "success", "cancelled": "critical"}
PAYMENT_STATUS_COLOR = {"pending": "warning", "paid": "success", "refunded": "info", "cancelled": "critical"}


def get_live_activity(user, limit=12):
    """
    A single, newest-first feed of real recent events — orders,
    reservations, and (Main Administrator only) account-recovery
    requests — built fresh from existing data on every call rather
    than a stored/persisted notification log, per the "use real
    database data, don't invent a notification table unless genuinely
    needed" rule. Each entry only appears if the viewer's Staff Access
    actually permits seeing that module (module ON + View ON — not
    just module ON, which used to be enough here and meant the View
    toggle did nothing for this feed). Order entries never include a
    monetary amount unless the viewer also has payments:view — a
    disabled Payments module must never leak revenue figures just
    because Orders happens to be visible.
    """
    from accounts.permissions import has_dashboard_action
    from django.urls import reverse

    items = []
    can_see_payment_amounts = has_dashboard_action(user, "payments", "view")

    if has_dashboard_action(user, "orders", "view"):
        Order = selectors._get_model("orders", "Order")
        if Order is not None:
            for order in Order.objects.prefetch_related("items").order_by("-created_at")[:limit]:
                item_count = order.items.count()
                item_text = f"{item_count} item{'s' if item_count != 1 else ''}"
                subtitle = f"{item_text} · ₦{order.total_amount:,.0f}" if can_see_payment_amounts else item_text
                items.append({
                    "color": ORDER_STATUS_COLOR.get(order.status, "info"),
                    "kind": "order",
                    "title": f"Order #{order.order_number} {order.get_status_display().lower()}",
                    "subtitle": subtitle,
                    "timestamp": order.created_at,
                    "url": reverse("orders:detail", args=[order.pk]) if _url_exists("orders:detail") else None,
                })

    if has_dashboard_action(user, "reservations", "view"):
        Reservation = selectors._get_model("reservations", "Reservation")
        if Reservation is not None:
            for reservation in Reservation.objects.order_by("-created_at")[:limit]:
                items.append({
                    "color": RESERVATION_STATUS_COLOR.get(reservation.status, "info"),
                    "kind": "reservation",
                    "title": f"Reservation for {reservation.full_name} — {reservation.get_status_display().lower()}",
                    "subtitle": f"{reservation.number_of_guests} guests · {reservation.reservation_date}",
                    "timestamp": reservation.created_at,
                    "url": reverse("reservations:list") if _url_exists("reservations:list") else None,
                })

    if user.is_superuser:
        from accounts.models import AccountRecoveryRequest, RecoveryRequestStatus

        for req in AccountRecoveryRequest.objects.filter(status=RecoveryRequestStatus.PENDING).order_by("-created_at")[:5]:
            items.append({
                "color": "warning",
                "kind": "recovery",
                "title": f"Account recovery request — {req.user}",
                "subtitle": "Awaiting your approval",
                "timestamp": req.created_at,
                "url": reverse("dashboard:staff_security"),
            })

    if has_dashboard_action(user, "inventory", "view"):
        try:
            from inventory.selectors import get_low_stock_ingredients

            for ingredient in get_low_stock_ingredients()[:5]:
                items.append({
                    "color": "warning",
                    "kind": "inventory",
                    "title": f"{ingredient.name} running low",
                    "subtitle": f"{ingredient.quantity_in_stock} {ingredient.unit} left (threshold {ingredient.low_stock_threshold} {ingredient.unit})",
                    "timestamp": ingredient.updated_at,
                    "url": reverse("inventory:ingredient_detail", args=[ingredient.pk]),
                })
        except ImportError:
            pass

    items.sort(key=lambda item: item["timestamp"], reverse=True)
    return items[:limit]


def _url_exists(name):
    from django.urls import NoReverseMatch, reverse

    try:
        reverse(name)
        return True
    except NoReverseMatch:
        return False


def sparkline_points(values, *, width=100, height=32, padding=3):
    """
    Converts a list of real numbers into an SVG polyline `points`
    string, normalized to fit the given viewBox — used for the stat
    card sparklines. A flat/empty series still returns a valid
    (flat-line) result rather than dividing by zero.
    """
    if not values:
        return f"0,{height / 2} {width},{height / 2}"

    lo, hi = min(values), max(values)
    span = hi - lo
    usable_h = height - 2 * padding
    step = width / max(len(values) - 1, 1)

    points = []
    for i, value in enumerate(values):
        x = i * step
        y = (padding + usable_h / 2) if span == 0 else (padding + usable_h - ((value - lo) / span) * usable_h)
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)
