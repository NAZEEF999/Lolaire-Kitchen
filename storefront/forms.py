from django import forms

from .validators import phone_number_validator


INPUT = (
    "w-full rounded-lg border border-cream-white/15 "
    "bg-ink-soft px-4 py-3 text-sm text-cream-white "
    "placeholder:text-cream-white/35 focus:outline-none "
    "focus:ring-2 focus:ring-ember/60 transition"
)


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {INPUT}".strip()


class AddToCartForm(forms.Form):
    menu_item_id = forms.IntegerField(
        widget=forms.HiddenInput
    )

    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
    )


class CheckoutForm(StyledFormMixin, forms.Form):
    full_name = forms.CharField(
        max_length=150,
        label="Full name",
    )

    phone_number = forms.CharField(
        max_length=20,
        validators=[phone_number_validator],
        label="Phone number",
    )

    email = forms.EmailField(
        required=False,
        label="Email (optional)",
    )

    delivery_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label="Delivery address (optional)",
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        label="Notes for the kitchen",
    )


class OrderLookupForm(StyledFormMixin, forms.Form):
    phone_number = forms.CharField(
        max_length=20,
        label="Phone number used at checkout",
    )

    order_number = forms.CharField(
        max_length=20,
        label="Order number (from your confirmation)",
    )


class ContactForm(StyledFormMixin, forms.Form):
    full_name = forms.CharField(
        max_length=150,
        label="Your name",
    )

    email = forms.EmailField(
        label="Email",
    )

    message = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Your message",
    )


class ReviewForm(StyledFormMixin, forms.Form):
    full_name = forms.CharField(
        max_length=150,
        label="Your name",
    )

    email = forms.EmailField(
        label="Email",
    )

    rating = forms.TypedChoiceField(
        choices=[
            (5, "★★★★★ — Excellent"),
            (4, "★★★★☆ — Very Good"),
            (3, "★★★☆☆ — Good"),
            (2, "★★☆☆☆ — Fair"),
            (1, "★☆☆☆☆ — Poor"),
        ],
        coerce=int,
        label="Rating",
    )

    review = forms.CharField(
        max_length=2000,
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": "Tell us about your experience...",
            }
        ),
        label="Your review",
    )