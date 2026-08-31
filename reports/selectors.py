"""
Database query logic for the reports app.

Reuses existing selectors/queryset methods from orders, customers,
menu, and tables wherever they already return what's needed. Only
new query *shapes* not covered anywhere else (grouped aggregates,
cross-model annotations, two-sided date ranges) are added here.
"""

from django.db.models import Count, Q, Sum

from customers.models import Customer
from menu.models import Category, MenuItem
from orders.models import Order
from tables.models import Table


def get_revenue_between(start_date, end_date):
    """Revenue for paid orders between two dates (inclusive). Reuses Order's .paid() queryset method."""
    return Order.objects.paid().filter(
        created_at__date__gte=start_date, created_at__date__lte=end_date
    ).aggregate(total=Sum("total_amount"))["total"] or 0


def get_orders_between(start_date, end_date):
    """Orders placed between two dates (inclusive)."""
    return Order.objects.select_related("customer", "table").filter(
        created_at__date__gte=start_date, created_at__date__lte=end_date
    )


def get_order_status_breakdown():
    return Order.objects.values("status").annotate(count=Count("id")).order_by("status")


def get_payment_status_breakdown():
    return Order.objects.values("payment_status").annotate(count=Count("id")).order_by("payment_status")


def get_payment_method_breakdown():
    return (
        Order.objects.exclude(payment_method="")
        .values("payment_method")
        .annotate(count=Count("id"))
        .order_by("payment_method")
    )


def get_menu_item_sales():
    """
    Active menu items annotated with units sold and revenue generated,
    excluding items from cancelled orders. One queryset serves best-
    selling, least-selling, and revenue-per-item reports.
    """
    sold_filter = Q(order_items__order__is_active=True) & ~Q(order_items__order__status="cancelled")
    return MenuItem.objects.annotate(
        units_sold=Sum("order_items__quantity", filter=sold_filter),
        item_revenue=Sum("order_items__line_total", filter=sold_filter),
    )


def get_category_order_volume():
    """Active categories annotated with total units ordered across all their items."""
    sold_filter = Q(menu_items__order_items__order__is_active=True) & ~Q(
        menu_items__order_items__order__status="cancelled"
    )
    return Category.objects.annotate(units_ordered=Sum("menu_items__order_items__quantity", filter=sold_filter))


def get_new_customers_between(start_date, end_date):
    """Active customers created between two dates (inclusive)."""
    return Customer.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)


def get_customer_order_frequency():
    """Active customers annotated with their (active) order count."""
    return Customer.objects.annotate(order_count=Count("orders", filter=Q(orders__is_active=True)))


def get_table_utilization():
    """Active tables annotated with how many (active) orders have used them."""
    return Table.objects.annotate(order_count=Count("orders", filter=Q(orders__is_active=True)))
