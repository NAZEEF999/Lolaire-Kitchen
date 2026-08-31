"""
Business logic for the menu app.

Views call into this module for anything that writes to the database,
keeping views.py lightweight per the project's BUSINESS LOGIC rule.
"""

from django.db import transaction

from .models import Category, MenuItem


def create_category(*, name, description="", display_order=0, is_active=True):
    return Category.objects.create(
        name=name, description=description, display_order=display_order, is_active=is_active
    )


def update_category(*, category, name=None, description=None, display_order=None, is_active=None):
    """Update a category's fields. Only the fields explicitly passed (not None) are changed."""
    fields_to_update = []

    if name is not None:
        category.name = name
        fields_to_update.append("name")
    if description is not None:
        category.description = description
        fields_to_update.append("description")
    if display_order is not None:
        category.display_order = display_order
        fields_to_update.append("display_order")
    if is_active is not None:
        category.is_active = is_active
        fields_to_update.append("is_active")

    if fields_to_update:
        fields_to_update.append("updated_at")
        category.save(update_fields=fields_to_update)

    return category


@transaction.atomic
def deactivate_category(*, category):
    """
    Soft-delete a category and cascade the soft-delete to its menu
    items — a genuinely multi-step write, so it's wrapped in a
    transaction to keep the category and its items consistent.
    """
    category.is_active = False
    category.save(update_fields=["is_active", "updated_at"])
    category.menu_items.update(is_active=False)
    return category


def create_menu_item(*, category, name, price, description="", image=None, is_available=True, is_active=True):
    return MenuItem.objects.create(
        category=category,
        name=name,
        description=description,
        price=price,
        image=image,
        is_available=is_available,
        is_active=is_active,
    )


def update_menu_item(
    *, menu_item, category=None, name=None, description=None, price=None,
    image=None, is_available=None, is_active=None,
):
    """Update a menu item's fields. Only the fields explicitly passed (not None) are changed."""
    fields_to_update = []

    if category is not None:
        menu_item.category = category
        fields_to_update.append("category")
    if name is not None:
        menu_item.name = name
        fields_to_update.append("name")
    if description is not None:
        menu_item.description = description
        fields_to_update.append("description")
    if price is not None:
        menu_item.price = price
        fields_to_update.append("price")
    if image is not None:
        menu_item.image = image
        fields_to_update.append("image")
    if is_available is not None:
        menu_item.is_available = is_available
        fields_to_update.append("is_available")
    if is_active is not None:
        menu_item.is_active = is_active
        fields_to_update.append("is_active")

    if fields_to_update:
        fields_to_update.append("updated_at")
        menu_item.save(update_fields=fields_to_update)

    return menu_item


def deactivate_menu_item(*, menu_item):
    """Soft-delete a single menu item."""
    menu_item.is_active = False
    menu_item.save(update_fields=["is_active", "updated_at"])
    return menu_item
