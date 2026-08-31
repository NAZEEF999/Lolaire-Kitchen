"""
Database query logic for the storefront app.

Reuses existing selectors from menu/orders/customers wherever they
already return what's needed — no query logic is duplicated.
"""

from menu import selectors as menu_selectors


def get_public_menu(*, category_slug=None, search=None):
    """Public menu browsing — reuses menu.selectors.get_menu_items(), filtered to available items only."""
    return menu_selectors.get_menu_items(category_slug=category_slug, is_available=True, search=search)


def get_public_categories():
    return menu_selectors.get_active_categories()


def get_menu_item_by_slug(slug):
    return menu_selectors.get_menu_item_by_slug(slug)


def get_order_for_lookup(*, phone_number, order_number):
    """
    Guest order lookup — returns a single Order only if BOTH the phone
    number and the exact order number match the same order, or None.
    Deliberately not "all orders for this phone number": a phone
    number alone isn't something only the customer knows (someone else
    could have it, or guess a common format), so a match on phone
    alone must never hand back someone's full order history. Requiring
    the specific order number too — which only someone who placed or
    was told about that order would have — keeps this a genuine,
    if lightweight, ownership check rather than a phone-number lookup.
    """
    from orders.models import Order

    return (
        Order.objects.select_related("customer")
        .prefetch_related("items__menu_item")
        .filter(order_number__iexact=order_number.strip(), customer__phone_number=phone_number)
        .first()
    )
