"""
Tests for the reservations app.
"""

from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import StaffAccess

from .models import Reservation

User = get_user_model()


def make_reservation(**kwargs):
    defaults = {
        "full_name": "Jane Doe",
        "phone_number": "08011112222",
        "reservation_date": date(2026, 12, 1),
        "reservation_time": time(19, 0),
        "number_of_guests": 2,
    }
    defaults.update(kwargs)
    return Reservation.objects.create(**defaults)


class PublicReservationAccessTests(TestCase):
    """
    Section 14 of the hardening pass: the customer-facing booking form
    must remain fully public — StaffAccessMiddleware must never apply
    to it, only to the separate staff management route below.
    """

    def test_public_create_page_accessible_without_login(self):
        response = self.client.get(reverse("reservations:create"))
        self.assertEqual(response.status_code, 200)

    def test_public_can_submit_a_reservation_without_login(self):
        response = self.client.post(reverse("reservations:create"), {
            "full_name": "Walk-in Guest",
            "phone_number": "08033334444",
            "email": "",
            "reservation_date": "2026-12-05",
            "reservation_time": "18:30",
            "number_of_guests": 4,
            "special_request": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Reservation.objects.filter(full_name="Walk-in Guest").exists())


class StaffReservationListAccessTests(TestCase):
    """Section 14: the staff management list requires reservations:view — previously only required being logged in."""

    def setUp(self):
        self.client = Client()
        make_reservation()
        self.granted = User.objects.create_user(username="granted1", password="pass12345")
        StaffAccess.objects.create(
            user=self.granted,
            dashboard_enabled=True,
            dashboard_sections={"reservations": True},
            dashboard_actions={"reservations": {"view": True, "manage": False}},
        )
        self.no_access = User.objects.create_user(username="noaccess1", password="pass12345")

    def test_staff_list_requires_login(self):
        response = self.client.get(reverse("reservations:list"))
        self.assertEqual(response.status_code, 302)

    def test_staff_list_requires_reservations_view_permission(self):
        self.client.login(username="noaccess1", password="pass12345")
        response = self.client.get(reverse("reservations:list"))
        self.assertEqual(response.status_code, 403)

    def test_staff_list_accessible_with_view_permission(self):
        self.client.login(username="granted1", password="pass12345")
        response = self.client.get(reverse("reservations:list"))
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_access_regardless_of_staffaccess(self):
        superuser = User.objects.create_superuser(username="root1", password="pass12345")
        self.client.login(username="root1", password="pass12345")
        response = self.client.get(reverse("reservations:list"))
        self.assertEqual(response.status_code, 200)
