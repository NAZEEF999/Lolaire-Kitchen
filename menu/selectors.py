"""
Database query logic for the menu app.

Read-only helpers used by views, services, and other apps (e.g. the
dashboard). Keeps ORM query construction out of views.py.
"""

from django.db.models import Count, Q

from .models import Category, MenuItem


def get_active_categories():
    """
    All active categories, ordered by display_order, annotated with a
    live count of their active menu items (avoids an N+1 query when
    the template shows a count per category).
    """
    return Category.objects.annotate(
        item_count=Count("menu_items", filter=Q(menu_items__is_active=True))
    ).order_by("display_order", "name")


def get_category_by_slug(slug):
    return Category.objects.filter(slug=slug).first()


def get_menu_items(*, category_slug=None, is_available=None, search=None):
    """
    Active menu items, optionally filtered by category, availability,
    and a search term matched against name/description.
    """
    queryset = MenuItem.objects.select_related("category")

    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)

    if is_available is not None:
        queryset = queryset.filter(is_available=is_available)

    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))

    return queryset


def get_menu_item_by_slug(slug):
    return MenuItem.objects.select_related("category").filter(slug=slug).first()
