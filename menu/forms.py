"""
ModelForms for the menu app.
"""

from django import forms

from .models import Category, MenuItem

TAILWIND_INPUT = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-blue-500"
)


class TailwindFormMixin:
    """
    Applies consistent Tailwind classes to every visible field widget.
    Mirrors accounts.forms.TailwindFormMixin, kept as a small local
    copy rather than imported, so the menu app doesn't depend on
    accounts for a purely cosmetic concern. A shared core.forms module
    would be a reasonable future refactor if this is needed by more apps.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {TAILWIND_INPUT}".strip()


class CategoryForm(TailwindFormMixin, forms.ModelForm):
    """
    Slug is intentionally excluded — it's generated automatically in
    Category.save() (see models.py / utils.generate_unique_slug).
    Uniqueness of `name` is validated by the model's unique=True field
    via full_clean(), which ModelForm.is_valid() calls automatically.
    """

    class Meta:
        model = Category
        fields = ["name", "description", "display_order", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class MenuItemForm(TailwindFormMixin, forms.ModelForm):
    """
    Slug is generated automatically in MenuItem.save(). Uniqueness of
    `name` within `category` is validated by the model's
    UniqueConstraint via full_clean(). Price non-negativity is
    validated by validators.validate_non_negative_price on the model
    field.
    """

    class Meta:
        model = MenuItem
        fields = ["category", "name", "description", "price", "image", "is_available", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
