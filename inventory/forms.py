"""
ModelForms for the inventory app.
"""

from django import forms

from .models import AdjustmentReason, Ingredient, Supplier

TAILWIND_INPUT = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-blue-500"
)


class TailwindFormMixin:
    """Mirrors accounts.forms.TailwindFormMixin — kept as a local copy per the project's established precedent (see menu.forms for the same note)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {TAILWIND_INPUT}".strip()


class IngredientForm(TailwindFormMixin, forms.ModelForm):
    opening_quantity = forms.DecimalField(
        required=False, min_value=0, initial=0, label="Opening stock quantity",
        help_text="Only used when creating a new ingredient.",
    )

    class Meta:
        model = Ingredient
        fields = ["name", "unit", "low_stock_threshold", "supplier"]


class IngredientUpdateForm(TailwindFormMixin, forms.ModelForm):
    """Separate from IngredientForm: editing an existing ingredient never touches quantity_in_stock directly — see inventory.services.record_stock_adjustment for the only path that does."""

    class Meta:
        model = Ingredient
        fields = ["name", "unit", "low_stock_threshold", "supplier", "is_active"]


class StockAdjustmentForm(TailwindFormMixin, forms.Form):
    reason = forms.ChoiceField(choices=AdjustmentReason.choices)
    quantity = forms.DecimalField(min_value=0.01, label="Quantity")
    direction = forms.ChoiceField(choices=[("add", "Add to stock"), ("remove", "Remove from stock")], initial="add")
    note = forms.CharField(required=False, max_length=255, widget=forms.TextInput(attrs={"placeholder": "Optional note"}))

    def signed_quantity(self):
        quantity = self.cleaned_data["quantity"]
        return quantity if self.cleaned_data["direction"] == "add" else -quantity


class SupplierForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "contact_name", "phone_number", "email", "is_active"]
