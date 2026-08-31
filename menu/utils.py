"""
Reusable helper functions for the menu app.
"""

from django.utils.text import slugify


def generate_unique_slug(model_class, name, *, scope_filters=None, exclude_pk=None):
    """
    Build a slug from `name` using Django's slugify(), then ensure it's
    unique for `model_class`, appending -2, -3, ... on collision.

    Checks against `model_class.all_objects` (unfiltered) so a slug is
    never reused from a soft-deleted row. `scope_filters` narrows the
    uniqueness check (e.g. {"category_id": category.id} to scope menu
    item slugs to their category, matching the "unique name per
    category" business rule). `exclude_pk` excludes the object being
    updated from the collision check.
    """
    scope_filters = scope_filters or {}
    base_slug = slugify(name)
    slug = base_slug
    counter = 2

    def slug_taken(candidate):
        queryset = model_class.all_objects.filter(slug=candidate, **scope_filters)
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        return queryset.exists()

    while slug_taken(slug):
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug
