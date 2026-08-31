"""
Template context processors for the storefront app.

Makes the cart item count available in every public template (for the
navbar cart badge) without every view having to pass it explicitly.
"""

from .utils import cart_item_count


def cart(request):
    return {"cart_count": cart_item_count(request)}
