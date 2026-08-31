
"""
Shared, reusable models for the project.

Every concrete model in the system should inherit TimeStampedModel so
that created_at / updated_at are always present and consistent.
"""

from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-updating created_at and
    updated_at fields.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class RestaurantSettings(TimeStampedModel):
    """
    Site-wide restaurant configuration.

    Normally the project should have only one active settings record.
    """

    CURRENCY_CHOICES = [
        ("NGN", "Nigerian Naira (₦)"),
        ("USD", "US Dollar ($)"),
        ("EUR", "Euro (€)"),
        ("GBP", "British Pound (£)"),
    ]

    restaurant_name = models.CharField(
        max_length=150,
        default="Lolaire's Kitchen",
    )

    tagline = models.CharField(
        max_length=255,
        blank=True,
        default="Good food. Great moments.",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    address = models.TextField(
        blank=True,
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Restaurant location for the Track Order map and Get Directions link. Look this up once on Google Maps (right-click the pin \u2192 copy coordinates).",
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    opening_hours = models.TextField(
        blank=True,
        help_text="Example: Mon-Sun: 10:00 AM - 10:00 PM",
    )

    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Enter percentage, e.g. 7.50 for 7.5%.",
    )

    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    about = models.TextField(
        blank=True,
    )

    instagram_url = models.URLField(
        blank=True,
    )

    facebook_url = models.URLField(
        blank=True,
    )

    twitter_url = models.URLField(
        blank=True,
        verbose_name="Twitter/X URL",
    )

    tiktok_url = models.URLField(
        blank=True,
        verbose_name="TikTok URL",
    )

    is_active = models.BooleanField(
        default=True,
    )

    # Currency settings
    base_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="NGN",
        help_text="Currency used for actual restaurant pricing and orders.",
    )

    display_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="NGN",
        help_text="Currency used when displaying converted prices to customers.",
    )

    exchange_rate_provider = models.CharField(
        max_length=100,
        default="CBN / Frankfurter",
        help_text="Source used for the exchange rate.",
    )

    exchange_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0,
        help_text="Number of display-currency units for 1 base-currency unit.",
    )

    exchange_rate_updated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the current exchange rate was last updated.",
    )

    auto_update_exchange_rate = models.BooleanField(
        default=True,
        help_text="Automatically refresh the exchange rate when the API integration is enabled.",
    )

    class Meta:
        verbose_name = "Restaurant Settings"
        verbose_name_plural = "Restaurant Settings"

    def __str__(self):
        return self.restaurant_name
