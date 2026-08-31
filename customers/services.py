"""
Business logic for the customers app.

Views call into this module for anything that writes to the database,
keeping views.py lightweight per the project's BUSINESS LOGIC rule.
"""

from .models import Customer
from .utils import normalize_phone_number


def create_customer(*, full_name, phone_number, email=None, address="", notes="", is_active=True):
    return Customer.objects.create(
        full_name=full_name,
        phone_number=normalize_phone_number(phone_number),
        email=email,
        address=address,
        notes=notes,
        is_active=is_active,
    )


def update_customer(
    *, customer, full_name=None, phone_number=None, email=None, address=None, notes=None, is_active=None
):
    """Update a customer's fields. Only the fields explicitly passed (not None) are changed."""
    fields_to_update = []

    if full_name is not None:
        customer.full_name = full_name
        fields_to_update.append("full_name")
    if phone_number is not None:
        customer.phone_number = normalize_phone_number(phone_number)
        fields_to_update.append("phone_number")
    if email is not None:
        customer.email = email
        fields_to_update.append("email")
    if address is not None:
        customer.address = address
        fields_to_update.append("address")
    if notes is not None:
        customer.notes = notes
        fields_to_update.append("notes")
    if is_active is not None:
        customer.is_active = is_active
        fields_to_update.append("is_active")

    if fields_to_update:
        fields_to_update.append("updated_at")
        customer.save(update_fields=fields_to_update)

    return customer


def deactivate_customer(*, customer):
    """Soft-delete a customer."""
    customer.is_active = False
    customer.save(update_fields=["is_active", "updated_at"])
    return customer
