"""
Custom validators for the inventory app.
"""

from django.core.validators import RegexValidator

# Mirrors accounts.validators.phone_number_validator — kept as a small
# local copy rather than imported, consistent with the precedent set
# across the rest of the project (customers, reservations, storefront
# each keep their own copy of this same rule).
phone_number_validator = RegexValidator(
    regex=r"^(?:\+234|0)[7-9][0-1]\d{8}$",
    message="Enter a valid Nigerian phone number, e.g. 08012345678 or +2348012345678.",
)
