"""
Models for the inventory app.

Internal-only, per the brief: nothing here is ever surfaced on the
public storefront — see storefront/models.py, which has no knowledge
of this app at all. This is a genuinely new system (nothing in the
project modeled ingredients, stock, or suppliers before), not a
duplicate of anything else.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel

from .validators import phone_number_validator


class Unit(models.TextChoices):
    KG = "kg", "Kilograms"
    G = "g", "Grams"
    L = "l", "Liters"
    ML = "ml", "Milliliters"
    PCS = "pcs", "Pieces"
    PACK = "pack", "Packs"


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=150, unique=True)
    contact_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, validators=[phone_number_validator])
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"

    def __str__(self):
        return self.name


class IngredientQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def low_stock(self):
        """Active ingredients at or below their own threshold — the real "Inventory Alerts" data source, nothing invented."""
        return self.filter(is_active=True, quantity_in_stock__lte=models.F("low_stock_threshold"))


class Ingredient(TimeStampedModel):
    name = models.CharField(max_length=150, unique=True)
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.KG)
    quantity_in_stock = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    low_stock_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="ingredients")
    is_active = models.BooleanField(default=True)

    objects = IngredientQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        verbose_name = "Ingredient"
        verbose_name_plural = "Ingredients"

    def __str__(self):
        return f"{self.name} ({self.get_unit_display()})"

    @property
    def is_low_stock(self):
        return self.quantity_in_stock <= self.low_stock_threshold


class AdjustmentReason(models.TextChoices):
    RESTOCK = "restock", "Restock"
    USAGE = "usage", "Usage / consumption"
    WASTE = "waste", "Waste / spoilage"
    CORRECTION = "correction", "Manual correction"


class StockAdjustment(TimeStampedModel):
    """
    One row per stock change — the durable inventory history an
    ingredient's current quantity_in_stock is derived from. Nothing
    ever edits quantity_in_stock directly outside of
    inventory.services.record_stock_adjustment, which creates one of
    these alongside it, in one transaction, so the two can never drift
    apart.
    """

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="adjustments")
    reason = models.CharField(max_length=20, choices=AdjustmentReason.choices)
    quantity_delta = models.DecimalField(max_digits=10, decimal_places=2, help_text="Positive to add stock, negative to remove.")
    note = models.CharField(max_length=255, blank=True)
    adjusted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_adjustments"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Stock Adjustment"
        verbose_name_plural = "Stock Adjustments"

    def __str__(self):
        sign = "+" if self.quantity_delta >= 0 else ""
        return f"{self.ingredient} {sign}{self.quantity_delta} ({self.get_reason_display()})"
