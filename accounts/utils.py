"""
Reusable helper functions for the accounts app.
"""

import re
import unicodedata


def generate_username(first_name, last_name):
    """
    Build a URL/DB-safe username suggestion from a staff member's
    name, e.g. "Ada Obi" -> "ada.obi". Does not guarantee uniqueness —
    callers should check against existing usernames and append a
    number if needed before saving.
    """
    base = f"{first_name} {last_name}".strip().lower()
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-z0-9]+", ".", base).strip(".")
    return base or "staff"


def role_label(role_value):
    """Return the human-readable label for a stored role value."""
    from .models import UserRole

    return UserRole(role_value).label
