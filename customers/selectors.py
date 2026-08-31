"""
Database query logic for the customers app.

Read-only helpers used by views and services. Keeps ORM query
construction out of views.py.
"""

from django.apps import apps as django_apps
from django.core.exceptions import FieldError
from django.db.models import Q

from .models import Customer


def _get_model(app_label, model_name):
    """Return the model class if it has been defined yet, else None."""
    try:
        return django_apps.get_model(app_label, model_name)
    except LookupError:
        return None


def get_customers(*, search=None):
    """Active customers, optionally filtered by a search term against name/phone/email."""
    queryset = Customer.objects.all()

    if search:
        queryset = queryset.filter(
            Q(full_name__icontains=search) | Q(phone_number__icontains=search) | Q(email__icontains=search)
        )

    return queryset


def get_customer_by_id(customer_id):
    return Customer.objects.filter(pk=customer_id).first()


def get_customer_by_phone(phone_number):
    return Customer.objects.filter(phone_number=phone_number).first()


def get_order_history(customer):
    """
    A customer's past orders. Looks up the Order model dynamically
    (mirroring the defensive lookup pattern in dashboard/selectors.py)
    rather than importing orders.models directly. Now that the orders
    app exists, this returns real data; the dynamic lookup is kept for
    resilience rather than importing orders.models at module level.
    """
    order_model = _get_model("orders", "Order")
    if order_model is None:
        return []
    try:
        return order_model.objects.filter(customer=customer)
    except FieldError:
        # The model exists but doesn't have the expected field(s) yet.
        return []
