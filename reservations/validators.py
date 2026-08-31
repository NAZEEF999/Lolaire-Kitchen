"""
Custom validators for the reservations app.
"""

from django.core.validators import MinValueValidator, RegexValidator

# Mirrors customers.validators.phone_number_validator — kept as a small
# local copy rather than imported, consistent with the precedent set
# there for accounts vs customers (each app owns its own copy of a
# rule that's coincidentally identical today).
phone_number_validator = RegexValidator(
    regex=r"^(?:\+234|0)[7-9][0-1]\d{8}$",
    message="Enter a valid Nigerian phone number, e.g. 08012345678 or +2348012345678.",
)

validate_positive_guest_count = MinValueValidator(1, message="Party size must be at least 1 guest.")
