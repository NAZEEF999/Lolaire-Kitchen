"""
Django admin registration for the reservations app, using Django
Unfold's ModelAdmin as the base class per the project's DJANGO ADMIN
rules — consistent with every other app.
"""

from django.contrib import admin
from django.contrib.admin import ModelAdmin

from core.admin_mixins import ModulePermissionAdminMixin

from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(ModulePermissionAdminMixin, ModelAdmin):
    lolaire_module = "reservations"
    list_display = (
        "full_name",
        "phone_number",
        "reservation_date",
        "reservation_time",
        "number_of_guests",
        "status",
        "is_active",
    )
    list_filter = ("status", "reservation_date", "is_active")
    search_fields = ("full_name", "phone_number", "email")
    ordering = ("-reservation_date", "-reservation_time")
    list_editable = ("status",)
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return Reservation.all_objects.all()
