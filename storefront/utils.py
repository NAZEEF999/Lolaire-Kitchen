"""Reusable helper functions for the storefront app."""

CART_SESSION_KEY = "cart"


def get_cart(request):
    """Cart is a plain dict in the session: {menu_item_id (str): quantity (int)}."""
    return request.session.get(CART_SESSION_KEY, {})


def save_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def cart_item_count(request):
    return sum(get_cart(request).values())
