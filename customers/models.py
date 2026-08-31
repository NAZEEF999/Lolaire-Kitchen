"""
Models for the customers app.

Soft deletion: is_active doubles as both "active/inactive status" and
the soft-delete flag, consistent with the pattern established in the
menu app — setting it to False is how a customer record is
"deleted" without removing the row.
"""

from django.db import models
from django.urls import reverse

from core.models import TimeStampedModel

from .validators import phone_number_validator


class CustomerQuerySet(models.QuerySet):
    """Chainable filters, mirroring menu.models.MenuQuerySet."""

    def active(self):
        return self.filter(is_active=True)


class ActiveCustomerManager(models.Manager.from_queryset(CustomerQuerySet)):
    """
    Default manager — returns only active customers, while still
    exposing .active() as an explicit, chainable QuerySet method for
    call sites that start from the unfiltered `all_objects` manager.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Customer(TimeStampedModel):
    full_name = models.CharField(max_length=150)
    # Unique: phone number is this system's primary way of recognizing
    # a returning customer, so duplicate records are prevented here.
    phone_number = models.CharField(max_length=20, unique=True, validators=[phone_number_validator])
    # Optional and not unique — not every customer provides an email,
    # and multiple family members may share one.
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Internal staff notes — not visible to the customer.")
    is_active = models.BooleanField(default=True)

    objects = ActiveCustomerManager()
    all_objects = models.Manager.from_queryset(CustomerQuerySet)()

    class Meta:
        ordering = ["full_name"]
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse("customers:detail", kwargs={"pk": self.pk})
