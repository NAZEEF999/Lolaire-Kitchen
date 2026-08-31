"""
Models for the tables app.

Soft deletion: is_active doubles as both "active/inactive status" and
the soft-delete flag, consistent with the pattern established in the
menu and customers apps.

TableStatus values are lowercase strings deliberately matching what
dashboard/selectors.py already queries for ("available", "occupied") —
see get_available_tables()/get_occupied_tables() there.
"""

from django.db import models
from django.urls import reverse

from core.models import TimeStampedModel

from .validators import validate_positive_capacity


class TableStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    OCCUPIED = "occupied", "Occupied"
    RESERVED = "reserved", "Reserved"
    CLEANING = "cleaning", "Cleaning"
    OUT_OF_SERVICE = "out_of_service", "Out of Service"


class TableQuerySet(models.QuerySet):
    """Chainable filters, mirroring menu.models.MenuQuerySet."""

    def active(self):
        return self.filter(is_active=True)

    def with_status(self, status):
        return self.filter(status=status)


class ActiveTableManager(models.Manager.from_queryset(TableQuerySet)):
    """
    Default manager — returns only active tables, while still exposing
    .active()/.with_status() as explicit, chainable QuerySet methods
    for call sites that start from the unfiltered `all_objects` manager.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Table(TimeStampedModel):
    table_number = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    capacity = models.PositiveIntegerField(validators=[validate_positive_capacity])
    status = models.CharField(max_length=20, choices=TableStatus.choices, default=TableStatus.AVAILABLE)
    location = models.CharField(max_length=100, blank=True, help_text="e.g. Patio, Main Floor, Upstairs.")
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    objects = ActiveTableManager()
    all_objects = models.Manager.from_queryset(TableQuerySet)()

    class Meta:
        ordering = ["table_number"]
        verbose_name = "Table"
        verbose_name_plural = "Tables"

    def __str__(self):
        return self.name or f"Table {self.table_number}"

    def get_absolute_url(self):
        return reverse("tables:detail", kwargs={"pk": self.pk})
