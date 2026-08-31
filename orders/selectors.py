"""
Database query logic for the orders app.

Read-only helpers used by views and services. Keeps ORM query
construction out of views.py. select_related()/prefetch_related() are
used wherever an order's related customer/table/items are needed
alongside it, to avoid N+1 queries.
"""

from django.db.models import Q, Sum
from django.utils import timezone

from .models import Order, OrderStatus


def get_order_detail_queryset():
    """select_related/prefetch_related tuned for the order detail page."""
    return Order.objects.select_related("customer", "table").prefetch_related("items__menu_item")


def get_orders(*, status=None, payment_status=None, search=None):
    """Active orders, optionally filtered by status/payment_status and a search term."""
    queryset = Order.objects.select_related("customer", "table")

    if status:
        queryset = queryset.filter(status=status)
    if payment_status:
        queryset = queryset.filter(payment_status=payment_status)
    if search:
        queryset = queryset.filter(
            Q(order_number__icontains=search)
            | Q(customer__full_name__icontains=search)
            | Q(customer__phone_number__icontains=search)
        )

    return queryset


def get_todays_orders():
    return Order.objects.select_related("customer", "table").for_date(timezone.localdate())


def get_pending_orders():
    return Order.objects.with_status(OrderStatus.PENDING)


def get_preparing_orders():
    return Order.objects.with_status(OrderStatus.PREPARING)


def get_ready_orders():
    return Order.objects.with_status(OrderStatus.READY)


def get_served_orders():
    return Order.objects.with_status(OrderStatus.SERVED)


def get_cancelled_orders():
    return Order.objects.with_status(OrderStatus.CANCELLED)


def get_unpaid_orders():
    return Order.objects.unpaid()


def get_paid_orders():
    return Order.objects.paid()


def get_revenue(*, since=None):
    """Sum of total_amount for paid orders, optionally since a given datetime."""
    queryset = Order.objects.paid()
    if since is not None:
        queryset = queryset.filter(created_at__gte=since)
    return queryset.aggregate(total=Sum("total_amount"))["total"] or 0


def get_order_history(*, customer=None, table=None):
    """Past orders for a given customer or table (whichever is provided)."""
    queryset = Order.objects.select_related("customer", "table").prefetch_related("items")
    if customer is not None:
        queryset = queryset.filter(customer=customer)
    if table is not None:
        queryset = queryset.filter(table=table)
    return queryset


def get_order_by_number(order_number):
    return Order.objects.filter(order_number=order_number).first()


def get_order_by_id(order_id):
    return Order.objects.select_related("customer", "table").filter(pk=order_id).first()
