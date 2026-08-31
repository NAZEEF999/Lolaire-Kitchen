"""
Forms for the orders app.

Per the project's POS PREPARATION requirements, no manual Order/OrderItem
ModelForm drives the main order-building flow — a future POS interface
will create Orders and OrderItems programmatically via services.py
(staff clicking menu items, not filling out a form). The forms below
exist only for this phase's placeholder-template actions: starting an
order, adding an item, and changing status — each a thin wrapper
around the same services.py functions that POS interface will call.
"""

from django import forms

from customers.models import Customer
from menu.models import MenuItem
from tables.models import Table

from .models import OrderStatus, PaymentStatus

TAILWIND_INPUT = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-blue-500"
)


class TailwindFormMixin:
    """
    Applies consistent Tailwind classes to every visible field widget.
    Mirrors the local copy pattern established in menu.forms /
    customers.forms / tables.forms.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {TAILWIND_INPUT}".strip()


class NewOrderForm(TailwindFormMixin, forms.Form):
    """Starts a new order — a future POS interface would set customer/table from context instead."""

    customer = forms.ModelChoiceField(queryset=Customer.objects.all(), required=False)
    table = forms.ModelChoiceField(queryset=Table.objects.all(), required=False)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))


class AddOrderItemForm(TailwindFormMixin, forms.Form):
    """Placeholder-template equivalent of clicking a menu item in a future POS cart."""

    menu_item = forms.ModelChoiceField(queryset=MenuItem.objects.filter(is_available=True))
    quantity = forms.IntegerField(min_value=1, initial=1)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))


class OrderStatusForm(TailwindFormMixin, forms.Form):
    status = forms.ChoiceField(choices=OrderStatus.choices)


class PaymentStatusForm(TailwindFormMixin, forms.Form):
    payment_status = forms.ChoiceField(choices=PaymentStatus.choices)
