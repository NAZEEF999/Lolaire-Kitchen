"""
Reusable helper functions for the customers app.
"""


def normalize_phone_number(value):
    """
    Strip whitespace so phone numbers are stored consistently, e.g.
    " 0801 234 5678" -> "08012345678". Used by services.py, which is
    the single write path for customer records, so normalization
    happens once regardless of whether the data came from a form, the
    admin, or a future import script.
    """
    return "".join(value.split())
