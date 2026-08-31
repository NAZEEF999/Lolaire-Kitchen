"""
Business logic for the inventory app.

Views call into this module for anything that writes to the database,
keeping views.py lightweight per the project's BUSINESS LOGIC rule.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Ingredient, StockAdjustment, Supplier


def create_ingredient(*, name, unit, low_stock_threshold, supplier=None, opening_quantity=0, actor=None):
    """
    Creates the ingredient, then records its starting stock as a real
    StockAdjustment (reason=restock) rather than just setting
    quantity_in_stock directly — so the history is complete from day
    one, and every unit of stock this ingredient ever has is
    traceable to an adjustment row.
    """
    with transaction.atomic():
        ingredient = Ingredient.objects.create(
            name=name, unit=unit, low_stock_threshold=low_stock_threshold, supplier=supplier, quantity_in_stock=0
        )
        if opening_quantity:
            record_stock_adjustment(
                ingredient=ingredient, reason="restock", quantity_delta=opening_quantity, note="Opening stock", actor=actor
            )
    return ingredient


def update_ingredient(*, ingredient, name=None, unit=None, low_stock_threshold=None, supplier=None, is_active=None):
    """Update an ingredient's fields. Only the fields explicitly passed (not None) are changed — quantity_in_stock is deliberately not settable here, see record_stock_adjustment."""
    fields_to_update = []

    if name is not None:
        ingredient.name = name
        fields_to_update.append("name")
    if unit is not None:
        ingredient.unit = unit
        fields_to_update.append("unit")
    if low_stock_threshold is not None:
        ingredient.low_stock_threshold = low_stock_threshold
        fields_to_update.append("low_stock_threshold")
    if supplier is not None:
        ingredient.supplier = supplier
        fields_to_update.append("supplier")
    if is_active is not None:
        ingredient.is_active = is_active
        fields_to_update.append("is_active")

    if fields_to_update:
        fields_to_update.append("updated_at")
        ingredient.save(update_fields=fields_to_update)

    return ingredient


def deactivate_ingredient(*, ingredient):
    """Soft-delete a single ingredient — matches the project's soft-deletion convention used everywhere else (menu, customers, etc.)."""
    ingredient.is_active = False
    ingredient.save(update_fields=["is_active", "updated_at"])
    return ingredient


@transaction.atomic
def record_stock_adjustment(*, ingredient, reason, quantity_delta, note="", actor=None):
    """
    The one path that ever changes quantity_in_stock — always paired
    with the StockAdjustment row that explains why, in the same
    transaction, so the running total and the history can never drift
    apart. quantity_delta is signed: positive adds stock (restock,
    correction upward), negative removes it (usage, waste, correction
    downward).

    Refuses to let quantity_in_stock go negative — a physical stock
    count below zero isn't a real state ("−5kg of chicken" doesn't
    mean anything), so this raises rather than silently clamping to
    zero, which would quietly lose the size of the discrepancy a
    clamp would otherwise hide. If this restaurant's workflow turns
    out to need negative inventory for some real reason (e.g.
    recording a shortfall discovered after the fact), that's a
    deliberate product decision to make explicitly, not a default to
    fall into silently.
    """
    new_quantity = ingredient.quantity_in_stock + quantity_delta
    if new_quantity < 0:
        raise ValidationError(
            f"This would take {ingredient.name} to {new_quantity} {ingredient.unit}, below zero. "
            f"Only {ingredient.quantity_in_stock} {ingredient.unit} is currently in stock."
        )

    adjustment = StockAdjustment.objects.create(
        ingredient=ingredient, reason=reason, quantity_delta=quantity_delta, note=note, adjusted_by=actor
    )
    ingredient.quantity_in_stock = new_quantity
    ingredient.save(update_fields=["quantity_in_stock", "updated_at"])
    return adjustment


def create_supplier(*, name, contact_name="", phone_number="", email="", is_active=True):
    return Supplier.objects.create(
        name=name, contact_name=contact_name, phone_number=phone_number, email=email, is_active=is_active
    )


def update_supplier(*, supplier, name=None, contact_name=None, phone_number=None, email=None, is_active=None):
    fields_to_update = []

    if name is not None:
        supplier.name = name
        fields_to_update.append("name")
    if contact_name is not None:
        supplier.contact_name = contact_name
        fields_to_update.append("contact_name")
    if phone_number is not None:
        supplier.phone_number = phone_number
        fields_to_update.append("phone_number")
    if email is not None:
        supplier.email = email
        fields_to_update.append("email")
    if is_active is not None:
        supplier.is_active = is_active
        fields_to_update.append("is_active")

    if fields_to_update:
        fields_to_update.append("updated_at")
        supplier.save(update_fields=fields_to_update)

    return supplier
