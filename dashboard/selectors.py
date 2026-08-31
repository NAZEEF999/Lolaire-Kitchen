"""
Database query logic for the dashboard app.

Dashboard statistics pull from the customers, menu, orders, tables,
reservations, and inventory apps — all of which are real, stable,
migrated apps in this project now. Each lookup here still guards
against FieldError specifically (a queryset referencing a field that
doesn't exist on the model), so a genuine future schema change fails
gracefully instead of crashing the whole dashboard — but nothing
broader than that is swallowed: an unexpected error (a real bug) is
allowed to raise and be seen, rather than silently displaying as 0.
"""

from datetime import timedelta

from django.apps import apps as django_apps
from django.core.exceptions import FieldError
from django.db.models import Sum
from django.utils import timezone


def _get_model(app_label, model_name):
    """Return the model class if it has been defined yet, else None."""
    try:
        return django_apps.get_model(app_label, model_name)
    except LookupError:
        return None


def _count(app_label, model_name, **filters):
    """Count rows for a model that may not exist yet, defaulting to 0."""
    model = _get_model(app_label, model_name)
    if model is None:
        return 0
    try:
        queryset = model.objects.filter(**filters) if filters else model.objects.all()
        return queryset.count()
    except FieldError:
        # Model exists but doesn't have the expected field(s) yet.
        return 0


def _sum_field(app_label, model_name, amount_field, since=None, **filters):
    """Sum a field for a model that may not exist yet, defaulting to 0."""
    model = _get_model(app_label, model_name)
    if model is None:
        return 0
    try:
        queryset = model.objects.filter(**filters) if filters else model.objects.all()
        if since is not None:
            queryset = queryset.filter(created_at__gte=since)
        return queryset.aggregate(total=Sum(amount_field))["total"] or 0
    except FieldError:
        return 0


def get_total_customers():
    return _count("customers", "Customer")


def get_total_menu_items():
    return _count("menu", "MenuItem")


def get_total_orders():
    return _count("orders", "Order")


def get_pending_orders():
    return _count("orders", "Order", status="pending")


def get_completed_orders():
    return _count("orders", "Order", status="served")


def get_available_tables():
    return _count("tables", "Table", status="available")


def get_occupied_tables():
    return _count("tables", "Table", status="occupied")


def get_daily_revenue():
    since = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return _sum_field("orders", "Order", "total_amount", since=since, payment_status="paid")


def get_weekly_revenue():
    since = timezone.now() - timedelta(days=7)
    return _sum_field("orders", "Order", "total_amount", since=since, payment_status="paid")


def get_monthly_revenue():
    since = timezone.now() - timedelta(days=30)
    return _sum_field("orders", "Order", "total_amount", since=since, payment_status="paid")


def get_todays_orders():
    today = timezone.localdate()
    return _count("orders", "Order", created_at__date=today)


def get_reservations_today():
    today = timezone.localdate()
    return _count("reservations", "Reservation", reservation_date=today)


def get_pending_reservations():
    return _count("reservations", "Reservation", status="pending")


def get_new_customers_today():
    today = timezone.localdate()
    return _count("customers", "Customer", created_at__date=today)


def get_cancelled_payments():
    """Real, existing PaymentStatus value — see orders.models.PaymentStatus (there's no "failed" status in this project, so this is the closest genuine signal of a payment needing attention)."""
    return _count("orders", "Order", payment_status="cancelled")


def get_popular_menu_items(limit=5):
    """Top menu items by total quantity ordered. Returns [] if orders/menu aren't ready yet."""
    OrderItem = _get_model("orders", "OrderItem")
    if OrderItem is None:
        return []
    try:
        from django.db.models import Sum

        rows = (
            OrderItem.objects.values("menu_item__name")
            .annotate(total_quantity=Sum("quantity"))
            .order_by("-total_quantity")[:limit]
        )
        return [{"name": row["menu_item__name"], "quantity": row["total_quantity"]} for row in rows]
    except FieldError:
        return []


def get_order_status_breakdown():
    """Count of orders per status. Returns {} if the orders app isn't ready yet."""
    Order = _get_model("orders", "Order")
    if Order is None:
        return {}
    try:
        from django.db.models import Count

        rows = Order.objects.values("status").annotate(total=Count("id"))
        return {row["status"]: row["total"] for row in rows}
    except FieldError:
        return {}


def get_orders_created_after(order_id, limit=20):
    """Orders with id greater than `order_id`, oldest first, capped at `limit` — used by the live-updates polling endpoint to find what's genuinely new since the client last checked. The cap matters regardless of what a well-behaved client sends: an endpoint must never structurally allow an unbounded response just because a caller passed since=0 or some other small value."""
    Order = _get_model("orders", "Order")
    if Order is None:
        return []
    try:
        return list(Order.objects.filter(id__gt=order_id).select_related("customer").order_by("id")[:limit])
    except FieldError:
        return []


def get_latest_order_id():
    Order = _get_model("orders", "Order")
    if Order is None:
        return 0
    try:
        latest = Order.objects.order_by("-id").first()
        return latest.id if latest else 0
    except FieldError:
        return 0


def get_daily_revenue_trend(days=7):
    """
    Real daily revenue — sum of `total_amount` for orders marked paid,
    grouped by day — for the last `days` days, oldest first. The
    actual data behind the Revenue stat card's sparkline and the
    Revenue Overview chart; days with no paid orders are real zeros,
    not gaps.
    """
    Order = _get_model("orders", "Order")
    if Order is None:
        return []
    from django.db.models.functions import TruncDate

    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    try:
        rows = (
            Order.objects.filter(created_at__date__gte=start, payment_status="paid")
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("total_amount"))
        )
        by_day = {row["day"]: float(row["total"] or 0) for row in rows}
    except FieldError:
        by_day = {}
    return [{"date": start + timedelta(days=i), "value": by_day.get(start + timedelta(days=i), 0.0)} for i in range(days)]


def get_daily_orders_trend(days=7):
    """Real order count per day for the last `days` days, oldest first — every order regardless of status, matching what "Total Orders" counts."""
    Order = _get_model("orders", "Order")
    if Order is None:
        return []
    from django.db.models import Count
    from django.db.models.functions import TruncDate

    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    try:
        rows = (
            Order.objects.filter(created_at__date__gte=start)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Count("id"))
        )
        by_day = {row["day"]: row["total"] for row in rows}
    except FieldError:
        by_day = {}
    return [{"date": start + timedelta(days=i), "value": by_day.get(start + timedelta(days=i), 0)} for i in range(days)]


def get_orders_by_status(status):
    """Real orders for one status, most recent first — the actual data behind each Order Pipeline column."""
    Order = _get_model("orders", "Order")
    if Order is None:
        return []
    try:
        return list(Order.objects.filter(status=status).select_related("table").prefetch_related("items").order_by("-created_at"))
    except FieldError:
        return []
