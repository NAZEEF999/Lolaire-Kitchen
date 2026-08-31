"""
Custom validators for the customers app.
"""

from django.core.validators import RegexValidator

# Mirrors accounts.validators.phone_number_validator — kept as a small
# local copy rather than imported, consistent with the precedent set
# in menu/forms.py, to avoid coupling the customers app to accounts
# for a rule that's coincidentally identical today but conceptually
# belongs to each app's own domain (staff numbers vs customer
# numbers). A shared core.validators module would be a reasonable
# future refactor if more apps need this.
phone_number_validator = RegexValidator(
    regex=r"^(?:\+234|0)[7-9][0-1]\d{8}$",
    message="Enter a valid Nigerian phone number, e.g. 08012345678 or +2348012345678.",
)
