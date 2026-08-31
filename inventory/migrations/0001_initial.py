from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import inventory.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Supplier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=150, unique=True)),
                ("contact_name", models.CharField(blank=True, max_length=150)),
                (
                    "phone_number",
                    models.CharField(blank=True, max_length=20, validators=[inventory.validators.phone_number_validator]),
                ),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Supplier",
                "verbose_name_plural": "Suppliers",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Ingredient",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=150, unique=True)),
                (
                    "unit",
                    models.CharField(
                        choices=[
                            ("kg", "Kilograms"),
                            ("g", "Grams"),
                            ("l", "Liters"),
                            ("ml", "Milliliters"),
                            ("pcs", "Pieces"),
                            ("pack", "Packs"),
                        ],
                        default="kg",
                        max_length=10,
                    ),
                ),
                ("quantity_in_stock", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("low_stock_threshold", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "supplier",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ingredients",
                        to="inventory.supplier",
                    ),
                ),
            ],
            options={
                "verbose_name": "Ingredient",
                "verbose_name_plural": "Ingredients",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="StockAdjustment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("restock", "Restock"),
                            ("usage", "Usage / consumption"),
                            ("waste", "Waste / spoilage"),
                            ("correction", "Manual correction"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "quantity_delta",
                    models.DecimalField(decimal_places=2, help_text="Positive to add stock, negative to remove.", max_digits=10),
                ),
                ("note", models.CharField(blank=True, max_length=255)),
                (
                    "adjusted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stock_adjustments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "ingredient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="adjustments", to="inventory.ingredient"
                    ),
                ),
            ],
            options={
                "verbose_name": "Stock Adjustment",
                "verbose_name_plural": "Stock Adjustments",
                "ordering": ["-created_at"],
            },
        ),
    ]
