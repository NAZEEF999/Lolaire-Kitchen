"""Project-wide query helpers shared across apps."""

from .models import RestaurantSettings


def get_active_settings():
    """
    Return the active RestaurantSettings row, or None if none exists
    yet. Callers (templates, views) must handle the None case — a
    fresh install has no settings row until a superuser creates one
    in /admin/.
    """
    return RestaurantSettings.objects.filter(is_active=True).first()
