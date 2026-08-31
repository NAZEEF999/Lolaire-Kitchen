"""
Tests for the customers app.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import StaffAccess, UserRole

from . import selectors, services
from .models import Customer
from .utils import normalize_phone_number
from .validators import phone_number_validator

User = get_user_model()


def make_customer(**kwargs):
    defaults = {"full_name": "Ada Obi", "phone_number": "08012345678"}
    defaults.update(kwargs)
    return Customer.objects.create(**defaults)


class CustomerModelTests(TestCase):
    def test_str_returns_full_name(self):
        customer = make_customer(full_name="Chidi Eze")
        self.assertEqual(str(customer), "Chidi Eze")

    def test_phone_number_must_be_unique(self):
        make_customer(phone_number="08011112222")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_customer(full_name="Other Person", phone_number="08011112222")

    def test_invalid_phone_number_fails_validation(self):
        customer = Customer(full_name="Bad Phone", phone_number="12345")
        with self.assertRaises(ValidationError):
            customer.full_clean()

    def test_email_and_address_and_notes_optional(self):
        customer = make_customer(phone_number="08099998888")
        self.assertEqual(customer.email, None)
        self.assertEqual(customer.address, "")
        self.assertEqual(customer.notes, "")

    def test_default_manager_excludes_inactive(self):
        active = make_customer(full_name="Active Person", phone_number="08011111111")
        inactive = make_customer(full_name="Inactive Person", phone_number="08022222222", is_active=False)
        self.assertIn(active, Customer.objects.all())
        self.assertNotIn(inactive, Customer.objects.all())
        self.assertIn(inactive, Customer.all_objects.all())

    def test_all_objects_active_chain(self):
        active = make_customer(full_name="Chained Active", phone_number="08033333333")
        make_customer(full_name="Chained Inactive", phone_number="08044444444", is_active=False)
        self.assertIn(active, Customer.all_objects.active())
        self.assertEqual(list(Customer.objects.all()), list(Customer.all_objects.active().order_by("full_name")))

    def test_get_absolute_url(self):
        customer = make_customer()
        self.assertEqual(customer.get_absolute_url(), f"/customers/{customer.pk}/")

    def test_audit_timestamps_present(self):
        customer = make_customer()
        self.assertIsNotNone(customer.created_at)
        self.assertIsNotNone(customer.updated_at)


class ValidatorTests(TestCase):
    def test_valid_phone_numbers_pass(self):
        phone_number_validator("08012345678")
        phone_number_validator("+2348012345678")

    def test_invalid_phone_number_raises(self):
        with self.assertRaises(ValidationError):
            phone_number_validator("not-a-phone")


class UtilTests(TestCase):
    def test_normalize_phone_number_strips_whitespace(self):
        self.assertEqual(normalize_phone_number(" 0801 234 5678"), "08012345678")

    def test_normalize_phone_number_no_op_on_clean_input(self):
        self.assertEqual(normalize_phone_number("08012345678"), "08012345678")


class SelectorTests(TestCase):
    def setUp(self):
        make_customer(full_name="Ada Obi", phone_number="08011111111", email="ada@example.com")
        make_customer(full_name="Tunde Bello", phone_number="08022222222")
        make_customer(full_name="Chidi Eze", phone_number="08033333333", is_active=False)

    def test_get_customers_excludes_inactive(self):
        self.assertEqual(selectors.get_customers().count(), 2)

    def test_get_customers_search_by_name(self):
        results = selectors.get_customers(search="ada")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().full_name, "Ada Obi")

    def test_get_customers_search_by_phone(self):
        results = selectors.get_customers(search="08022222222")
        self.assertEqual(results.count(), 1)

    def test_get_customers_search_by_email(self):
        results = selectors.get_customers(search="ada@example.com")
        self.assertEqual(results.count(), 1)

    def test_get_customer_by_phone(self):
        customer = selectors.get_customer_by_phone("08011111111")
        self.assertIsNotNone(customer)
        self.assertEqual(customer.full_name, "Ada Obi")

    def test_get_customer_by_id(self):
        customer = make_customer(full_name="Lookup Me", phone_number="08055555555")
        found = selectors.get_customer_by_id(customer.pk)
        self.assertEqual(found, customer)

    def test_get_order_history_returns_empty_for_customer_with_no_orders(self):
        customer = Customer.objects.first()
        # list() normalizes both of get_order_history()'s possible return
        # types — a literal [] (defensive fallback if the orders app were
        # ever absent) or a real empty QuerySet (now that it exists) —
        # since QuerySet doesn't define __eq__ against a list literal.
        self.assertEqual(list(selectors.get_order_history(customer)), [])


class ServiceTests(TestCase):
    def test_create_customer_normalizes_phone_number(self):
        customer = services.create_customer(full_name="New Customer", phone_number=" 0801 234 5678")
        self.assertEqual(customer.phone_number, "08012345678")

    def test_update_customer_only_changes_provided_fields(self):
        customer = make_customer(full_name="Original Name", address="Old Address")
        services.update_customer(customer=customer, address="New Address")
        customer.refresh_from_db()
        self.assertEqual(customer.full_name, "Original Name")
        self.assertEqual(customer.address, "New Address")

    def test_update_customer_normalizes_phone_number(self):
        customer = make_customer(phone_number="08099990000")
        services.update_customer(customer=customer, phone_number=" 0802 000 0000")
        customer.refresh_from_db()
        self.assertEqual(customer.phone_number, "08020000000")

    def test_deactivate_customer(self):
        customer = make_customer()
        services.deactivate_customer(customer=customer)
        customer.refresh_from_db()
        self.assertFalse(customer.is_active)


class CustomerViewAccessTests(TestCase):
    """Access decided entirely by StaffAccess now — see menu.tests.MenuViewAccessTests for the same rewrite reasoning."""

    def setUp(self):
        self.client = Client()
        self.customer = make_customer(full_name="Jollof Fan", phone_number="08066667777")
        self.admin = User.objects.create_user(username="admin1", password="pass12345", role=UserRole.ADMINISTRATOR)
        StaffAccess.objects.create(
            user=self.admin,
            dashboard_enabled=True,
            dashboard_sections={"customers": True},
            dashboard_actions={"customers": {"view": True, "create": True, "edit": True, "delete": True}},
        )
        self.waiter = User.objects.create_user(username="waiter1", password="pass12345", role=UserRole.WAITER)
        StaffAccess.objects.create(
            user=self.waiter,
            dashboard_enabled=True,
            dashboard_sections={"customers": True},
            dashboard_actions={"customers": {"view": True, "create": False, "edit": False, "delete": False}},
        )
        self.no_access_waiter = User.objects.create_user(username="waiter2", password="pass12345", role=UserRole.WAITER)

    def test_list_requires_login(self):
        response = self.client.get(reverse("customers:list"))
        self.assertEqual(response.status_code, 302)

    def test_list_requires_customers_view_permission(self):
        self.client.login(username="waiter2", password="pass12345")
        response = self.client.get(reverse("customers:list"))
        self.assertEqual(response.status_code, 403)

    def test_list_accessible_with_view_permission(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("customers:list"))
        self.assertEqual(response.status_code, 200)

    def test_list_search(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("customers:list"), {"q": "Jollof"})
        self.assertContains(response, "Jollof Fan")

    def test_detail_accessible_with_view_permission(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("customers:detail", args=[self.customer.pk]))
        self.assertEqual(response.status_code, 200)

    def test_waiter_without_create_action_cannot_create_customer(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("customers:create"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_customer(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(reverse("customers:create"), {
            "full_name": "Newly Added",
            "phone_number": "08088889999",
            "email": "",
            "address": "",
            "notes": "",
            "is_active": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Customer.objects.filter(full_name="Newly Added").exists())

    def test_admin_can_delete_customer_soft_deletes(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(reverse("customers:delete", args=[self.customer.pk]))
        self.assertEqual(response.status_code, 302)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)
        self.assertTrue(Customer.all_objects.filter(pk=self.customer.pk).exists())

    def test_waiter_without_delete_action_cannot_delete_customer(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.post(reverse("customers:delete", args=[self.customer.pk]))
        self.assertEqual(response.status_code, 403)
