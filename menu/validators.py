"""
Custom validators for the menu app.

Uniqueness rules (category names unique; menu item names unique per
category) are enforced at the model/database level via unique=True
and a UniqueConstraint in models.py, which is the Django-recommended
approach — no custom uniqueness validators are needed here.

The one rule that needs an explicit validator is price: Django's
built-in MinValueValidator already does this robustly, so it's reused
directly rather than reimplemented.
"""

from django.core.validators import MinValueValidator

validate_non_negative_price = MinValueValidator(0, message="Price cannot be negative.")
