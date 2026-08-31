"""
Custom validators for the accounts app.
"""

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# Accepts local (0801...) or international (+234801...) Nigerian mobile
# numbers. Staff phone numbers are optional, but if one is entered it
# must be well-formed.
phone_number_validator = RegexValidator(
    regex=r"^(?:\+234|0)[7-9][0-1]\d{8}$",
    message="Enter a valid Nigerian phone number, e.g. 08012345678 or +2348012345678.",
)


def validate_role_change_allowed(user, new_role):
    """
    Raise ValidationError if changing `user`'s role away from
    Administrator would leave the system with zero Administrators.

    Deferred imports avoid a circular import between validators.py and
    models.py at module load time.
    """
    from .models import UserRole

    if user.role == UserRole.ADMINISTRATOR and new_role != UserRole.ADMINISTRATOR:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        remaining = (
            User.objects.filter(role=UserRole.ADMINISTRATOR)
            .exclude(pk=user.pk)
            .count()
        )
        if remaining == 0:
            raise ValidationError(
                "Cannot change the role of the last remaining Administrator."
            )
