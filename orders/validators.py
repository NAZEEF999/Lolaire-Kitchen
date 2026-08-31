"""
Custom validators for the orders app.
"""

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

validate_positive_quantity = MinValueValidator(1, message="Quantity must be greater than zero.")
validate_non_negative_amount = MinValueValidator(0, message="Amount cannot be negative.")


def validate_menu_item_is_active(menu_item):
    """Raise ValidationError if the given menu item is inactive (soft-deleted) and cannot be ordered."""
    if not menu_item.is_active:
        raise ValidationError("This menu item is no longer available and cannot be added to an order.")
