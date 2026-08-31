"""
Reusable helper functions for the orders app.
"""

from django.utils import timezone


def generate_order_number(model_class):
    """
    Build a unique, human-readable order number like "ORD-20260805-0001",
    scoped to the current day. Mirrors the collision-safe generation
    loop used in menu.utils.generate_unique_slug. Checks against
    `model_class.all_objects` (unfiltered) so a number is never reused
    from a soft-deleted order.
    """
    today = timezone.localdate()
    prefix = f"ORD-{today.strftime('%Y%m%d')}-"
    counter = 1
    while True:
        candidate = f"{prefix}{counter:04d}"
        if not model_class.all_objects.filter(order_number=candidate).exists():
            return candidate
        counter += 1
