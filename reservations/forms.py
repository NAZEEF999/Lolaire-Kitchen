"""
Forms for the reservations app.
"""

from django import forms
from django.utils import timezone

from .models import Reservation

_INPUT_CLASSES = (
    "w-full rounded-lg border border-ink/15 bg-cream px-4 py-3 text-sm text-ink "
    "placeholder:text-inksoft/60 focus:outline-none focus:ring-2 focus:ring-gold focus:border-gold"
)


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            "full_name",
            "phone_number",
            "email",
            "reservation_date",
            "reservation_time",
            "number_of_guests",
            "special_request",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": _INPUT_CLASSES, "placeholder": "Your full name"}),
            "phone_number": forms.TextInput(attrs={"class": _INPUT_CLASSES, "placeholder": "08012345678"}),
            "email": forms.EmailInput(attrs={"class": _INPUT_CLASSES, "placeholder": "you@example.com"}),
            "reservation_date": forms.DateInput(attrs={"class": _INPUT_CLASSES, "type": "date"}),
            "reservation_time": forms.TimeInput(attrs={"class": _INPUT_CLASSES, "type": "time"}),
            "number_of_guests": forms.NumberInput(attrs={"class": _INPUT_CLASSES, "min": 1}),
            "special_request": forms.Textarea(
                attrs={"class": _INPUT_CLASSES, "rows": 4, "placeholder": "Anniversary, allergies, seating preference…"}
            ),
        }
        labels = {
            "full_name": "Full name",
            "phone_number": "Phone number",
            "email": "Email (optional)",
            "reservation_date": "Date",
            "reservation_time": "Time",
            "number_of_guests": "Number of guests",
            "special_request": "Special request / message",
        }

    def clean_reservation_date(self):
        reservation_date = self.cleaned_data["reservation_date"]
        if reservation_date < timezone.localdate():
            raise forms.ValidationError("Please choose a date that isn't in the past.")
        return reservation_date
