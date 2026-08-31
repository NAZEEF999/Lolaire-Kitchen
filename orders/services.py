"""
Business logic for the orders app.

Views call into this module for anything that writes to the database,
keeping views.py lightweight per the project's BUSINESS LOGIC rule.
Every multi-step operation (more than one row written) is wrapped in
transaction.atomic() so it succeeds or fails as a whole.

Cross-app integration: this module calls tables.services to keep a
table's status in sync with the orders assigned to it. This is a
one-directional dependency (orders -> tables); tables has no knowledge
of orders, keeping the layering clean.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum

from tables import services as table_services
from tables.models import TableStatus

from .models import Order, OrderItem, OrderStatus, PaymentStatus
from .validators import validate_menu_item_is_active, validate_positive_quantity


def _ensure_order_is_editable(*, order, acting_user):
    """
    Enforces: "Served orders cannot be edited except by someone with
    Orders Edit permission." Previously checked
    `acting_user.is_administrator` (the legacy `role` field) — that
    was a second, independent permission system living underneath
    StaffAccess, which is exactly what this hardening pass exists to
    remove. Uses has_dashboard_action so a superuser always passes
    regardless of any StaffAccess row, matching every other action
    check in the project.
    """
    from accounts.permissions import has_dashboard_action

    if order.status == OrderStatus.SERVED and not (acting_user and has_dashboard_action(acting_user, "orders", "edit")):
        raise PermissionDenied("Served orders can only be edited by staff with Orders edit permission.")


@transaction.atomic
def create_order(*, customer=None, table=None, notes="", delivery_address="", delivery_latitude=None, delivery_longitude=None, acting_user=None):
    """
    Create a new, empty order (Pending, no items yet) — matches the
    POS flow: staff opens an order, then adds items one at a time via
    add_order_item(). If a table is provided, it's marked Occupied.
    """
    order = Order.objects.create(
        customer=customer,
        table=table,
        status=OrderStatus.PENDING,
        payment_status=PaymentStatus.PENDING,
        notes=notes,
        delivery_address=delivery_address,
        delivery_latitude=delivery_latitude,
        delivery_longitude=delivery_longitude,
    )
    if table is not None:
        table_services.change_table_status(table=table, new_status=TableStatus.OCCUPIED)
    return order


@transaction.atomic
def add_order_item(*, order, menu_item, quantity, notes="", acting_user=None):
    """
    Add an item to an order. unit_price/line_total are computed
    automatically in OrderItem.save() (price snapshot) — this
    function never sets them directly.
    """
    _ensure_order_is_editable(order=order, acting_user=acting_user)
    validate_menu_item_is_active(menu_item)
    validate_positive_quantity(quantity)

    item = OrderItem.objects.create(order=order, menu_item=menu_item, quantity=quantity, notes=notes)
    calculate_totals(order=order)
    return item


@transaction.atomic
def update_order_item(*, order_item, quantity=None, notes=None, acting_user=None):
    """
    Update an existing order item's quantity/notes. unit_price is
    never changed here — see OrderItem.save() / module docstring in
    models.py for why.
    """
    _ensure_order_is_editable(order=order_item.order, acting_user=acting_user)

    changed = False
    if quantity is not None:
        validate_positive_quantity(quantity)
        order_item.quantity = quantity
        changed = True
    if notes is not None:
        order_item.notes = notes
        changed = True

    if changed:
        order_item.save()  # line_total recomputed automatically in OrderItem.save()
        calculate_totals(order=order_item.order)

    return order_item


@transaction.atomic
def remove_order_item(*, order_item, acting_user=None):
    """Remove an item from an order and recompute totals."""
    order = order_item.order
    _ensure_order_is_editable(order=order, acting_user=acting_user)
    order_item.delete()
    calculate_totals(order=order)


def calculate_totals(*, order):
    """
    Recompute subtotal from the order's current items, then save.
    Order.save() enforces total_amount = subtotal - discount_amount +
    tax_amount as an invariant, so total_amount is always correct
    afterward regardless of what discount_amount/tax_amount currently hold.
    """
    order.subtotal = order.items.aggregate(total=Sum("line_total"))["total"] or Decimal("0.00")
    order.save(update_fields=["subtotal", "total_amount", "updated_at"])
    return order


@transaction.atomic
def change_order_status(*, order, new_status, acting_user=None):
    """
    The single path for changing an order's status. When the new
    status is Served or Cancelled, the assigned table (if any) is
    automatically released back to Available (via release_table()).
    """
    if new_status not in OrderStatus.values:
        raise ValidationError(f"'{new_status}' is not a valid order status.")

    _ensure_order_is_editable(order=order, acting_user=acting_user)

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])

    if new_status in (OrderStatus.SERVED, OrderStatus.CANCELLED):
        release_table(order=order)

    return order


def change_payment_status(*, order, new_payment_status):
    """
    The single path for changing an order's payment status. This is
    the integration point a future payment provider (e.g. Paystack)
    will call — from a webhook/callback — once payment confirmation
    arrives, without needing any change to the Order model itself.
    """
    if new_payment_status not in PaymentStatus.values:
        raise ValidationError(f"'{new_payment_status}' is not a valid payment status.")
    order.payment_status = new_payment_status
    order.save(update_fields=["payment_status", "updated_at"])
    return order


@transaction.atomic
def assign_table(*, order, table):
    """Assign (or reassign) a table to an order and mark it Occupied."""
    order.table = table
    order.save(update_fields=["table", "updated_at"])
    table_services.change_table_status(table=table, new_status=TableStatus.OCCUPIED)
    return order


@transaction.atomic
def release_table(*, order):
    """
    Free up the order's assigned table, if any, marking it Available —
    but only if no other active order still claims that table (avoids
    marking a table Available while a different order is still using it).
    Called automatically by change_order_status() when an order becomes
    Served or Cancelled; also usable directly.
    """
    if order.table_id is None:
        return order

    table = order.table
    order.table = None
    order.save(update_fields=["table", "updated_at"])

    still_in_use = Order.objects.filter(
        table=table, status__in=[OrderStatus.PENDING, OrderStatus.PREPARING, OrderStatus.READY]
    ).exists()
    if not still_in_use:
        table_services.change_table_status(table=table, new_status=TableStatus.AVAILABLE)

    return order


@transaction.atomic
def cancel_order(*, order, acting_user=None):
    """Cancel an order — releases its table and marks payment Cancelled if it was still Pending."""
    change_order_status(order=order, new_status=OrderStatus.CANCELLED, acting_user=acting_user)
    if order.payment_status == PaymentStatus.PENDING:
        change_payment_status(order=order, new_payment_status=PaymentStatus.CANCELLED)
    return order


@transaction.atomic
def complete_order(*, order, acting_user=None):
    """Mark an order Served — releases its table (via change_order_status)."""
    return change_order_status(order=order, new_status=OrderStatus.SERVED, acting_user=acting_user)
