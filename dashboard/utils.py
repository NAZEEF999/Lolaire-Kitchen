"""
Reusable helper functions for the dashboard app.
"""


def format_currency(amount):
    """Format a numeric amount as Nigerian Naira for display, e.g. ₦12,500.00."""
    return f"\u20a6{amount:,.2f}"
