"""
Models for the menu app.

Soft deletion: the field list for both models includes `is_active`
but no dedicated "deleted" flag, so is_active doubles as the soft-
delete flag — setting it to False is how a Category or MenuItem is
"deleted" without removing the row. The default `objects` manager
only returns is_active=True rows; `all_objects` exposes everything,
including soft-deleted rows, for admin/reporting use.
"""

from cloudinary.models import CloudinaryField
from django.db import models
from django.urls import reverse

from core.models import TimeStampedModel

from .utils import generate_unique_slug
from .validators import validate_non_negative_price


class MenuQuerySet(models.QuerySet):
    """Shared chainable filters for Category and MenuItem."""

    def active(self):
        return self.filter(is_active=True)


class MenuItemQuerySet(MenuQuerySet):
    def available(self):
        return self.filter(is_available=True)


class ActiveManager(models.Manager.from_queryset(MenuQuerySet)):
    """
    Default manager for Category — returns only non-soft-deleted
    (is_active=True) rows, while still exposing .active() as an
    explicit, chainable QuerySet method for call sites that start from
    the unfiltered `all_objects` manager (e.g. Category.all_objects.active()).
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class ActiveMenuItemManager(models.Manager.from_queryset(MenuItemQuerySet)):
    """Same as ActiveManager, plus MenuItemQuerySet's .available() chain method."""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Category(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    objects = ActiveManager()
    all_objects = models.Manager.from_queryset(MenuQuerySet)()

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Category, self.name, exclude_pk=self.pk)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("menu:category_detail", kwargs={"slug": self.slug})


class MenuItem(TimeStampedModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="menu_items",
        help_text="PROTECT: prevents a category from being hard-deleted while it still "
        "has items — use the soft-delete (is_active) flow instead.",
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[validate_non_negative_price])
    image = CloudinaryField("image", blank=True, null=True)
    is_available = models.BooleanField(
        default=True, help_text="Temporarily out of stock — different from is_active (soft delete)."
    )
    is_featured = models.BooleanField(
        default=False, help_text="Show this item in the public homepage's Featured Menu section."
    )
    is_active = models.BooleanField(default=True)

    objects = ActiveMenuItemManager()
    all_objects = models.Manager.from_queryset(MenuItemQuerySet)()

    class Meta:
        ordering = ["category__display_order", "name"]
        verbose_name = "Menu Item"
        verbose_name_plural = "Menu Items"
        constraints = [
            models.UniqueConstraint(fields=["category", "name"], name="unique_menu_item_name_per_category"),
        ]

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(
                MenuItem, self.name, scope_filters={"category_id": self.category_id}, exclude_pk=self.pk
            )
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("menu:item_detail", kwargs={"slug": self.slug})
