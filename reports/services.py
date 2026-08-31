"""
Business logic for the reports app.

Report-building services compose selectors — this app's own and the
existing ones in orders/customers/menu/tables — into plain data
structures (dicts, lists, querysets), so a future PDF/Excel export
view can call these exact functions instead of a template.
"""

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from customers import selectors as customer_selectors
from orders import selectors as order_selectors
from orders.models import OrderStatus, PaymentMethod, PaymentStatus

from . import selectors


# ── Revenue reports (daily/weekly/monthly reuse orders.selectors.get_revenue) ──

def get_daily_revenue_report():
    since = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return {"period": "Today", "revenue": order_selectors.get_revenue(since=since)}


def get_weekly_revenue_report():
    since = timezone.now() - timedelta(days=7)
    return {"period": "Last 7 days", "revenue": order_selectors.get_revenue(since=since)}


def get_monthly_revenue_report():
    since = timezone.now() - timedelta(days=30)
    return {"period": "Last 30 days", "revenue": order_selectors.get_revenue(since=since)}


def get_custom_range_revenue_report(*, start_date, end_date):
    return {"period": f"{start_date} to {end_date}", "revenue": selectors.get_revenue_between(start_date, end_date)}


# ── Sales report (units/revenue, reusing get_menu_item_sales for all three views) ──

def get_best_selling_items(limit=10):
    return list(selectors.get_menu_item_sales().filter(units_sold__gt=0).order_by("-units_sold")[:limit])


def get_least_selling_items(limit=10):
    return list(selectors.get_menu_item_sales().filter(units_sold__gt=0).order_by("units_sold")[:limit])


def get_revenue_per_menu_item():
    return selectors.get_menu_item_sales().filter(item_revenue__gt=0).order_by("-item_revenue")


def get_most_ordered_categories(limit=10):
    return list(selectors.get_category_order_volume().filter(units_ordered__gt=0).order_by("-units_ordered")[:limit])


# ── Orders report ──

def get_order_status_report():
    labels = dict(OrderStatus.choices)
    return [
        {"status": row["status"], "label": labels.get(row["status"], row["status"]), "count": row["count"]}
        for row in selectors.get_order_status_breakdown()
    ]


def get_payment_status_report():
    labels = dict(PaymentStatus.choices)
    return [
        {
            "payment_status": row["payment_status"],
            "label": labels.get(row["payment_status"], row["payment_status"]),
            "count": row["count"],
        }
        for row in selectors.get_payment_status_breakdown()
    ]


def get_payment_method_report():
    labels = dict(PaymentMethod.choices)
    return [
        {
            "payment_method": row["payment_method"],
            "label": labels.get(row["payment_method"], row["payment_method"]),
            "count": row["count"],
        }
        for row in selectors.get_payment_method_breakdown()
    ]


def get_orders_between_report(*, start_date, end_date, status=None, payment_status=None, payment_method=None):
    orders = selectors.get_orders_between(start_date, end_date)
    if status:
        orders = orders.filter(status=status)
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    if payment_method:
        orders = orders.filter(payment_method=payment_method)
    return orders


# ── Customer report ──

def get_total_customers_report():
    return customer_selectors.get_customers().count()


def get_new_customers_report(*, start_date, end_date):
    return selectors.get_new_customers_between(start_date, end_date)


def get_most_frequent_customers(limit=10):
    return list(selectors.get_customer_order_frequency().filter(order_count__gt=0).order_by("-order_count")[:limit])


def get_customer_history_summary(*, customer):
    """Reuses orders.selectors.get_order_history() and summarizes it."""
    history = order_selectors.get_order_history(customer=customer)
    summary = history.aggregate(order_count=Count("id"), total_spent=Sum("total_amount"))
    return {
        "customer": customer,
        "order_count": summary["order_count"] or 0,
        "total_spent": summary["total_spent"] or 0,
        "orders": history,
    }


# ── Table utilization report ──

def get_table_utilization_report():
    return selectors.get_table_utilization().order_by("-order_count")


def get_most_used_tables(limit=10):
    return list(selectors.get_table_utilization().filter(order_count__gt=0).order_by("-order_count")[:limit])


def get_least_used_tables(limit=10):
    return list(selectors.get_table_utilization().order_by("order_count")[:limit])
