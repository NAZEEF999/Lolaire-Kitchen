"""
Models for the reservations app.

Public visitors create Reservation rows directly from the website
(no login required — see views.py). Staff triage/manage them from the
Django admin, using `status` to move a reservation through its
lifecycle and `is_active` as the soft-delete flag, consistent with
the pattern established in menu/customers/tables/orders.
"""

from django.db import models


from core.models import TimeStampedModel

from .validators import phone_number_validator, validate_positive_guest_count


class ReservationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


class ReservationQuerySet(models.QuerySet):
    """Chainable filters, mirroring the pattern in menu/customers/tables/orders."""

    def active(self):
        return self.filter(is_active=True)

    def with_status(self, status):
        return self.filter(status=status)

    def upcoming(self):
        return self.filter(status__in=[ReservationStatus.PENDING, ReservationStatus.CONFIRMED])


class ActiveReservationManager(models.Manager.from_queryset(ReservationQuerySet)):
    """Default manager — returns only active (non-soft-deleted) reservations."""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Reservation(TimeStampedModel):
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20, validators=[phone_number_validator])
    email = models.EmailField(blank=True, null=True)
    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    number_of_guests = models.PositiveIntegerField(validators=[validate_positive_guest_count])
    special_request = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ReservationStatus.choices, default=ReservationStatus.PENDING)
    is_active = models.BooleanField(default=True)

    objects = ActiveReservationManager()
    all_objects = models.Manager.from_queryset(ReservationQuerySet)()

    class Meta:
        ordering = ["-reservation_date", "-reservation_time"]
        verbose_name = "Reservation"
        verbose_name_plural = "Reservations"

    def __str__(self):
        return f"{self.full_name} — {self.reservation_date} {self.reservation_time} ({self.number_of_guests} guests)"
