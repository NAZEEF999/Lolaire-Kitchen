"""
Tests for the tables app.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import StaffAccess, UserRole

from . import selectors, services
from .models import Table, TableStatus

User = get_user_model()


def make_table(**kwargs):
    defaults = {"table_number": 1, "capacity": 4}
    defaults.update(kwargs)
    return Table.objects.create(**defaults)


class TableModelTests(TestCase):
    def test_str_uses_name_if_present(self):
        table = make_table(table_number=2, name="Window Booth")
        self.assertEqual(str(table), "Window Booth")

    def test_str_falls_back_to_table_number(self):
        table = make_table(table_number=3)
        self.assertEqual(str(table), "Table 3")

    def test_table_number_must_be_unique(self):
        make_table(table_number=5)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_table(table_number=5)

    def test_capacity_must_be_greater_than_zero(self):
        table = Table(table_number=10, capacity=0)
        with self.assertRaises(ValidationError):
            table.full_clean()

    def test_default_status_is_available(self):
        table = make_table(table_number=6)
        self.assertEqual(table.status, TableStatus.AVAILABLE)

    def test_default_manager_excludes_inactive(self):
        active = make_table(table_number=7)
        inactive = make_table(table_number=8, is_active=False)
        self.assertIn(active, Table.objects.all())
        self.assertNotIn(inactive, Table.objects.all())
        self.assertIn(inactive, Table.all_objects.all())

    def test_all_objects_active_and_with_status_chain(self):
        occupied = make_table(table_number=9, status=TableStatus.OCCUPIED)
        available = make_table(table_number=11, status=TableStatus.AVAILABLE)
        make_table(table_number=12, status=TableStatus.OCCUPIED, is_active=False)

        occupied_active = Table.all_objects.active().with_status(TableStatus.OCCUPIED)
        self.assertIn(occupied, occupied_active)
        self.assertNotIn(available, occupied_active)

    def test_get_absolute_url(self):
        table = make_table(table_number=13)
        self.assertEqual(table.get_absolute_url(), f"/tables/{table.pk}/")

    def test_ordering_by_table_number(self):
        make_table(table_number=30)
        make_table(table_number=10)
        make_table(table_number=20)
        numbers = list(Table.objects.values_list("table_number", flat=True))
        self.assertEqual(numbers, [10, 20, 30])


class SelectorTests(TestCase):
    def setUp(self):
        make_table(table_number=1, status=TableStatus.AVAILABLE)
        make_table(table_number=2, status=TableStatus.OCCUPIED)
        make_table(table_number=3, status=TableStatus.OCCUPIED)
        make_table(table_number=4, status=TableStatus.CLEANING, is_active=False)

    def test_get_tables_no_filter_excludes_inactive(self):
        self.assertEqual(selectors.get_tables().count(), 3)

    def test_get_tables_filters_by_status(self):
        self.assertEqual(selectors.get_tables(status=TableStatus.OCCUPIED).count(), 2)

    def test_get_available_tables(self):
        self.assertEqual(selectors.get_available_tables().count(), 1)

    def test_get_occupied_tables(self):
        self.assertEqual(selectors.get_occupied_tables().count(), 2)

    def test_get_table_by_number(self):
        table = selectors.get_table_by_number(1)
        self.assertIsNotNone(table)
        self.assertEqual(table.status, TableStatus.AVAILABLE)

    def test_get_table_by_id(self):
        table = make_table(table_number=99)
        found = selectors.get_table_by_id(table.pk)
        self.assertEqual(found, table)


class ServiceTests(TestCase):
    def test_create_table_always_starts_available(self):
        table = services.create_table(table_number=50, capacity=6)
        self.assertEqual(table.status, TableStatus.AVAILABLE)

    def test_update_table_only_changes_provided_fields(self):
        table = make_table(table_number=51, capacity=4, location="Main Floor")
        services.update_table(table=table, location="Patio")
        table.refresh_from_db()
        self.assertEqual(table.capacity, 4)
        self.assertEqual(table.location, "Patio")

    def test_update_table_does_not_accept_status_kwarg(self):
        table = make_table(table_number=52)
        with self.assertRaises(TypeError):
            services.update_table(table=table, status=TableStatus.OCCUPIED)

    def test_change_table_status(self):
        table = make_table(table_number=53)
        services.change_table_status(table=table, new_status=TableStatus.RESERVED)
        table.refresh_from_db()
        self.assertEqual(table.status, TableStatus.RESERVED)

    def test_change_table_status_rejects_invalid_value(self):
        table = make_table(table_number=54)
        with self.assertRaises(ValidationError):
            services.change_table_status(table=table, new_status="not_a_real_status")

    def test_deactivate_table(self):
        table = make_table(table_number=55, status=TableStatus.AVAILABLE)
        services.deactivate_table(table=table)
        table.refresh_from_db()
        self.assertFalse(table.is_active)

    def test_deactivate_occupied_table_raises(self):
        table = make_table(table_number=56, status=TableStatus.OCCUPIED)
        with self.assertRaises(ValidationError):
            services.deactivate_table(table=table)
        table.refresh_from_db()
        self.assertTrue(table.is_active)


class TableViewAccessTests(TestCase):
    """
    Access decided entirely by StaffAccess now — see
    menu.tests.MenuViewAccessTests for the same rewrite reasoning.
    Also covers this hardening pass's other tables-specific fix:
    TableStatusUpdateView now requires tables:edit (previously any
    logged-in staff member could change a table's status regardless
    of StaffAccess).
    """

    def setUp(self):
        self.client = Client()
        self.table = make_table(table_number=100, capacity=4)
        self.admin = User.objects.create_user(username="admin1", password="pass12345", role=UserRole.ADMINISTRATOR)
        StaffAccess.objects.create(
            user=self.admin,
            dashboard_enabled=True,
            dashboard_sections={"tables": True},
            dashboard_actions={"tables": {"view": True, "create": True, "edit": True, "delete": True}},
        )
        self.waiter = User.objects.create_user(username="waiter1", password="pass12345", role=UserRole.WAITER)
        StaffAccess.objects.create(
            user=self.waiter,
            dashboard_enabled=True,
            dashboard_sections={"tables": True},
            dashboard_actions={"tables": {"view": True, "create": False, "edit": True, "delete": False}},
        )
        self.view_only_waiter = User.objects.create_user(username="waiter2", password="pass12345", role=UserRole.WAITER)
        StaffAccess.objects.create(
            user=self.view_only_waiter,
            dashboard_enabled=True,
            dashboard_sections={"tables": True},
            dashboard_actions={"tables": {"view": True, "create": False, "edit": False, "delete": False}},
        )
        self.no_access_waiter = User.objects.create_user(username="waiter3", password="pass12345", role=UserRole.WAITER)

    def test_list_requires_login(self):
        response = self.client.get(reverse("tables:list"))
        self.assertEqual(response.status_code, 302)

    def test_list_requires_tables_view_permission(self):
        self.client.login(username="waiter3", password="pass12345")
        response = self.client.get(reverse("tables:list"))
        self.assertEqual(response.status_code, 403)

    def test_list_accessible_with_view_permission(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("tables:list"))
        self.assertEqual(response.status_code, 200)

    def test_detail_accessible_with_view_permission(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("tables:detail", args=[self.table.pk]))
        self.assertEqual(response.status_code, 200)

    def test_waiter_without_create_action_cannot_create_table(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("tables:create"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_table(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(reverse("tables:create"), {
            "table_number": 200,
            "name": "",
            "capacity": 2,
            "location": "",
            "notes": "",
            "is_active": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Table.objects.filter(table_number=200).exists())

    def test_waiter_with_edit_action_can_update_table_status(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.post(reverse("tables:status_update", args=[self.table.pk]), {"status": "occupied"})
        self.assertEqual(response.status_code, 302)
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, TableStatus.OCCUPIED)

    def test_view_only_waiter_cannot_update_table_status(self):
        """The gap this hardening pass closed: previously ANY logged-in staff member could update table status regardless of StaffAccess."""
        self.client.login(username="waiter2", password="pass12345")
        response = self.client.post(reverse("tables:status_update", args=[self.table.pk]), {"status": "occupied"})
        self.assertEqual(response.status_code, 403)
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, TableStatus.AVAILABLE)

    def test_admin_can_delete_available_table(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(reverse("tables:delete", args=[self.table.pk]))
        self.assertEqual(response.status_code, 302)
        self.table.refresh_from_db()
        self.assertFalse(self.table.is_active)

    def test_admin_cannot_delete_occupied_table(self):
        self.table.status = TableStatus.OCCUPIED
        self.table.save(update_fields=["status"])
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(reverse("tables:delete", args=[self.table.pk]))
        self.assertEqual(response.status_code, 302)
        self.table.refresh_from_db()
        self.assertTrue(self.table.is_active)

    def test_waiter_without_delete_action_cannot_delete_table(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.post(reverse("tables:delete", args=[self.table.pk]))
        self.assertEqual(response.status_code, 403)
