"""
Models for the orders app — the core business module.

Soft deletion: is_active doubles as the soft-delete flag, consistent
with every other app in this project.

Snapshot pricing: OrderItem.unit_price is copied from MenuItem.price
the moment an item is first saved and is never re-read from MenuItem
afterward — this is what keeps historical orders accurate even after
menu prices change. This is enforced in OrderItem.save() itself
(triggered whenever self.pk is None, i.e. on first creation) rather
than only in services.py, so it holds true regardless of entry point
(services, the Django admin inline, a shell, etc).

Total invariant: Order.save() always recomputes
total_amount = subtotal - discount_amount + tax_amount before saving,
so total_amount can never drift out of sync with those three fields —
whether they were changed via services.calculate_totals() or edited
directly (e.g. a discount entered in the admin).

Payment gateway readiness: payment_status/payment_method are plain
fields on Order updated exclusively through
services.change_payment_status() — a future payment provider (e.g.
Paystack) integrates by calling that same function from a
webhook/callback. No change to this model is needed to add one.
"""

from decimal import Decimal
import uuid

from django.db import models
from django.urls import reverse

from core.models import TimeStampedModel
from customers.models import Customer
from menu.models import MenuItem
from tables.models import Table

from .utils import generate_order_number
from .validators import validate_non_negative_amount, validate_positive_quantity


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PREPARING = "preparing", "Preparing"
    READY = "ready", "Ready"
    SERVED = "served", "Served"
    CANCELLED = "cancelled", "Cancelled"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    REFUNDED = "refunded", "Refunded"
    CANCELLED = "cancelled", "Cancelled"


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Cash"
    CARD = "card", "Card"
    TRANSFER = "transfer", "Transfer"
    POS = "pos", "POS"
    ONLINE = "online", "Online"


class OrderQuerySet(models.QuerySet):
    """Chainable filters, mirroring the pattern in menu/tables/customers."""

    def active(self):
        return self.filter(is_active=True)

    def with_status(self, status):
        return self.filter(status=status)

    def unpaid(self):
        return self.exclude(payment_status=PaymentStatus.PAID)

    def paid(self):
        return self.filter(payment_status=PaymentStatus.PAID)

    def for_date(self, date):
        return self.filter(created_at__date=date)


class ActiveOrderManager(models.Manager.from_queryset(OrderQuerySet)):
    """Default manager — returns only active (non-soft-deleted) orders."""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Order(TimeStampedModel):
    order_number = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    # Public-facing confirmation pages must never be reachable by
    # guessing — order_number is sequential per day (ORD-20260805-0001,
    # -0002, ...) and was never meant to double as a secret. This is
    # the identifier storefront.urls actually uses for the public
    # order-confirmation page; order_number stays for staff-facing
    # display and the Dashboard/Admin, where it's fine to be readable
    # and sequential since those are already behind login.
    confirmation_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    table = models.ForeignKey(
        Table, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), editable=False)
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[validate_non_negative_amount]
    )
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[validate_non_negative_amount]
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), editable=False)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, blank=True)
    notes = models.TextField(blank=True)
    delivery_address = models.TextField(
        blank=True,
        help_text="Only set for storefront delivery orders — blank for dine-in/table orders.",
    )
    delivery_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        help_text="Best-effort geocode of delivery_address, used to plot the Track Order map. May be blank if geocoding failed or wasn't attempted.",
    )
    delivery_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
    )
    is_active = models.BooleanField(default=True)

    objects = ActiveOrderManager()
    all_objects = models.Manager.from_queryset(OrderQuerySet)()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = generate_order_number(Order)
        # Invariant: total_amount always reflects the current
        # subtotal/discount/tax, regardless of what changed or which
        # code path (service, admin, shell) triggered this save.
        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("orders:detail", kwargs={"pk": self.pk})


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(validators=[validate_positive_quantity])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"

    def save(self, *args, **kwargs):
        if self.pk is None:
            # New item: snapshot the menu item's current price. Never
            # re-read menu_item.price after this point — see module
            # docstring.
            self.unit_price = self.menu_item.price
        self.line_total = self.unit_price * self.quantity
        super().save(*args, **kwargs)
