"""
ModelForms for the customers app.
"""

from django import forms

from .models import Customer

TAILWIND_INPUT = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-blue-500"
)


class TailwindFormMixin:
    """
    Applies consistent Tailwind classes to every visible field widget.
    Mirrors accounts.forms.TailwindFormMixin / menu.forms.TailwindFormMixin
    — kept as a small local copy, consistent with the precedent set in
    the menu app, rather than imported across apps for a cosmetic concern.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {TAILWIND_INPUT}".strip()


class CustomerForm(TailwindFormMixin, forms.ModelForm):
    """
    Uniqueness of phone_number is validated by the model's unique=True
    field via full_clean(), which ModelForm.is_valid() calls
    automatically — no custom uniqueness check needed here.
    """

    class Meta:
        model = Customer
        fields = ["full_name", "phone_number", "email", "address", "notes", "is_active"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
