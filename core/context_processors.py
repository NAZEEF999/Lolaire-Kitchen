"""Project-wide template context processors."""

from . import selectors


def restaurant_settings(request):
    """
    Makes the active RestaurantSettings row available to every
    template as `restaurant_settings`, so contact info, address, and
    location data can be pulled dynamically instead of hardcoded per
    template. Value is None if no settings row exists yet — templates
    using this should fall back gracefully (e.g. `{% if
    restaurant_settings %}`), not assume it's always present.
    """
    return {"restaurant_settings": selectors.get_active_settings()}
