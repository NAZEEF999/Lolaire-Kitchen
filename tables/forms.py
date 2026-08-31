"""
Forms for the tables app.
"""

from django import forms

from .models import Table, TableStatus

TAILWIND_INPUT = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-blue-500"
)


class TailwindFormMixin:
    """
    Applies consistent Tailwind classes to every visible field widget.
    Mirrors the local copy pattern established in menu.forms /
    customers.forms.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {TAILWIND_INPUT}".strip()


class TableForm(TailwindFormMixin, forms.ModelForm):
    """
    Status is intentionally excluded — status changes go through
    TableStatusForm / services.change_table_status(), the single path
    for status transitions per the project's business rules.
    Uniqueness of table_number is validated by the model's unique=True
    field via full_clean(), which ModelForm.is_valid() calls automatically.
    """

    class Meta:
        model = Table
        fields = ["table_number", "name", "capacity", "location", "notes", "is_active"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class TableStatusForm(TailwindFormMixin, forms.Form):
    """A small, focused form for the one thing it does: change a table's status."""

    status = forms.ChoiceField(choices=TableStatus.choices)
