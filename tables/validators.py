"""
Custom validators for the tables app.

Uniqueness of table_number is enforced at the model level via
unique=True — no custom validator needed. Seating capacity greater
than zero reuses Django's built-in MinValueValidator, same pattern as
menu.validators.validate_non_negative_price.
"""

from django.core.validators import MinValueValidator

validate_positive_capacity = MinValueValidator(1, message="Seating capacity must be greater than zero.")
