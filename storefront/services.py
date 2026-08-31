"""
Business logic for the storefront app.

Checkout deliberately does NOT duplicate order-creation logic.
It calls orders.services.create_order()/add_order_item() and
customers.services.create_customer() directly, using the same
business logic as the staff POS flow.
"""

from decimal import Decimal

import requests

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse

from customers import selectors as customer_selectors
from customers import services as customer_services
from core.services import geocode_address
from menu.models import MenuItem
from orders import services as order_services

from .utils import get_cart


def get_cart_lines(request):
    """
    Resolve the session cart into:
    (menu_item, quantity, line_total) tuples.

    Unavailable or stale items are skipped.
    """
    cart = get_cart(request)

    if not cart:
        return [], Decimal("0.00")

    items = (
        MenuItem.objects
        .filter(
            pk__in=cart.keys(),
            is_available=True,
        )
        .select_related("category")
    )

    lines = []
    subtotal = Decimal("0.00")

    for item in items:
        quantity = cart.get(str(item.pk), 0)

        if quantity <= 0:
            continue

        line_total = item.price * quantity
        subtotal += line_total

        lines.append(
            {
                "menu_item": item,
                "quantity": quantity,
                "line_total": line_total,
            }
        )

    return lines, subtotal


@transaction.atomic
def checkout_cart(
    *,
    request,
    full_name,
    phone_number,
    email="",
    delivery_address="",
    notes="",
):
    """
    Turn the session cart into a real Order.

    Matches an existing Customer by phone number, or creates one.
    """
    lines, _subtotal = get_cart_lines(request)

    if not lines:
        raise ValidationError("Your cart is empty.")

    customer = customer_selectors.get_customer_by_phone(
        phone_number
    )

    if customer is None:
        customer = customer_services.create_customer(
            full_name=full_name,
            phone_number=phone_number,
            email=email or None,
            address=delivery_address,
        )
    elif delivery_address and not customer.address:
        # Fill in a blank profile address as a convenience for next
        # time, but never silently overwrite an address the customer
        # already has on file — they might be ordering to a different
        # place (office, a friend's house) just this once.
        customer_services.update_customer(customer=customer, address=delivery_address)

    delivery_latitude, delivery_longitude = geocode_address(delivery_address) if delivery_address else (None, None)

    order = order_services.create_order(
        customer=customer,
        table=None,
        notes=notes,
        delivery_address=delivery_address,
        delivery_latitude=delivery_latitude,
        delivery_longitude=delivery_longitude,
    )

    for line in lines:
        order_services.add_order_item(
            order=order,
            menu_item=line["menu_item"],
            quantity=line["quantity"],
        )

    return order


PAYSTACK_INITIALIZE_URL = (
    "https://api.paystack.co/transaction/initialize"
)

PAYSTACK_VERIFY_URL = (
    "https://api.paystack.co/transaction/verify/{reference}"
)


def initialize_paystack_transaction(*, request, order, email):
    """
    Initialize a Paystack transaction for an existing Order.

    NGN amounts are converted from naira to kobo.
    """

    if not settings.PAYSTACK_SECRET_KEY:
        raise ValidationError(
            "Paystack is not configured."
        )

    if not email:
        raise ValidationError(
            "An email address is required for online payment."
        )

    if order.total_amount <= 0:
        raise ValidationError(
            "This order has no payable amount."
        )

    reference = (
        f"LOLAIRE-{order.pk}-"
        f"{order.confirmation_token.hex[:12]}"
    )

    callback_url = request.build_absolute_uri(
        reverse("storefront:paystack_callback")
    )

    payload = {
        "email": email,
        "amount": int(order.total_amount * 100),
        "currency": "NGN",
        "reference": reference,
        "callback_url": callback_url,
        "metadata": {
            "order_id": order.pk,
            "order_number": order.order_number,
            "confirmation_token": str(
                order.confirmation_token
            ),
        },
    }

    response = requests.post(
        PAYSTACK_INITIALIZE_URL,
        json=payload,
        headers={
            "Authorization": (
                f"Bearer {settings.PAYSTACK_SECRET_KEY}"
            ),
            "Content-Type": "application/json",
        },
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("status"):
        raise ValidationError(
            data.get(
                "message",
                "Paystack could not initialize the payment.",
            )
        )

    return data["data"]


def verify_paystack_transaction(*, reference):
    """
    Verify a Paystack transaction server-side.
    """

    if not settings.PAYSTACK_SECRET_KEY:
        raise ValidationError(
            "Paystack is not configured."
        )

    if not reference:
        raise ValidationError(
            "Payment reference is required."
        )

    response = requests.get(
        PAYSTACK_VERIFY_URL.format(
            reference=reference
        ),
        headers={
            "Authorization": (
                f"Bearer {settings.PAYSTACK_SECRET_KEY}"
            )
        },
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("status"):
        raise ValidationError(
            data.get(
                "message",
                "Paystack verification failed.",
            )
        )

    return data["data"]