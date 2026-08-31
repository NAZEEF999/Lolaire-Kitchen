"""
Filter forms for the reports app.
"""

from django import forms

from orders.models import OrderStatus, PaymentMethod, PaymentStatus

TAILWIND_INPUT = (
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:outline-none focus:ring-2 focus:ring-blue-500"
)


class TailwindFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {TAILWIND_INPUT}".strip()


class DateRangeForm(TailwindFormMixin, forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date must be before end date.")
        return cleaned_data


class OrderReportFilterForm(TailwindFormMixin, forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    status = forms.ChoiceField(choices=[("", "Any status")] + list(OrderStatus.choices), required=False)
    payment_status = forms.ChoiceField(
        choices=[("", "Any payment status")] + list(PaymentStatus.choices), required=False
    )
    payment_method = forms.ChoiceField(
        choices=[("", "Any payment method")] + list(PaymentMethod.choices), required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date must be before end date.")
        return cleaned_data
