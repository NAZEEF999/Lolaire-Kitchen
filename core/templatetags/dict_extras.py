"""Small template-filter library for dictionary lookups by variable key."""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Usage: {{ mydict|get_item:key_variable }} — Django's dot lookup only supports literal keys."""
    if not dictionary:
        return None
    return dictionary.get(key)
