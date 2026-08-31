"""Custom validators for the storefront app."""

from django.core.validators import RegexValidator

phone_number_validator = RegexValidator(
    regex=r"^(?:\+234|0)[7-9][0-1]\d{8}$",
    message="Enter a valid Nigerian phone number, e.g. 08012345678 or +2348012345678.",
)
