"""
Tests for the dashboard app.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import StaffAccess

from . import selectors, services

User = get_user_model()

ALL_STAT_KEYS = {
    "total_customers", "new_customers_today", "total_menu_items", "total_orders", "todays_orders",
    "pending_orders", "completed_orders", "available_tables", "occupied_tables", "reservations_today",
    "pending_reservations", "daily_revenue", "weekly_revenue", "monthly_revenue", "cancelled_payments",
    "low_stock_count",
}


def _staff_user(username, **access_kwargs):
    """Creates a non-superuser staff account with a StaffAccess row — access_kwargs override specific fields (e.g. dashboard_enabled=True, dashboard_sections={...})."""
    user = User.objects.create_user(username=username, password="pass12345")
    StaffAccess.objects.create(user=user, **access_kwargs)
    return user


class SelectorDefensiveLookupTests(TestCase):
    """
    Every selector here must return 0 when there's no data — either
    because the underlying app doesn't exist yet (the original reason
    this defensive lookup pattern was built) or, now that
    customers/menu/orders/tables all exist, simply because no rows
    have been created in this test's empty database. Both cases must
    degrade gracefully to 0 rather than raising.
    """

    def test_total_customers_returns_zero(self):
        self.assertEqual(selectors.get_total_customers(), 0)

    def test_total_menu_items_returns_zero(self):
        self.assertEqual(selectors.get_total_menu_items(), 0)

    def test_total_orders_returns_zero(self):
        self.assertEqual(selectors.get_total_orders(), 0)

    def test_pending_orders_returns_zero(self):
        self.assertEqual(selectors.get_pending_orders(), 0)

    def test_completed_orders_returns_zero(self):
        self.assertEqual(selectors.get_completed_orders(), 0)

    def test_available_tables_returns_zero(self):
        self.assertEqual(selectors.get_available_tables(), 0)

    def test_occupied_tables_returns_zero(self):
        self.assertEqual(selectors.get_occupied_tables(), 0)

    def test_daily_revenue_returns_zero(self):
        self.assertEqual(selectors.get_daily_revenue(), 0)

    def test_weekly_revenue_returns_zero(self):
        self.assertEqual(selectors.get_weekly_revenue(), 0)

    def test_monthly_revenue_returns_zero(self):
        self.assertEqual(selectors.get_monthly_revenue(), 0)

    def test_unknown_model_lookup_returns_none(self):
        self.assertIsNone(selectors._get_model("customers", "Customer"))


class DashboardStatisticsServiceTests(TestCase):
    def test_get_dashboard_statistics_has_all_expected_keys(self):
        stats = services.get_dashboard_statistics()
        self.assertEqual(set(stats.keys()), ALL_STAT_KEYS)

    def test_filter_stats_by_permission_superuser_sees_everything(self):
        superuser = User.objects.create_superuser(username="root1", password="pass12345")
        stats = services.filter_stats_by_permission(superuser, services.get_dashboard_statistics())
        self.assertEqual(set(stats.keys()), ALL_STAT_KEYS)

    def test_filter_stats_by_permission_hides_payments_when_module_off(self):
        """StaffAccess is the only thing that decides this now — not role. See STAT_MODULE_OWNER."""
        user = _staff_user("waiter1", dashboard_sections={"orders": True, "tables": True})
        stats = services.filter_stats_by_permission(user, services.get_dashboard_statistics())
        self.assertNotIn("daily_revenue", stats)
        self.assertNotIn("cancelled_payments", stats)
        self.assertIn("pending_orders", stats)
        self.assertIn("available_tables", stats)

    def test_filter_stats_by_permission_shows_payments_when_granted(self):
        """The key regression this whole pass exists to prevent: a Waiter-ish account with Payments explicitly ON via StaffAccess must see payment stats, regardless of any job-title label."""
        user = _staff_user("frontofhouse1", dashboard_sections={"payments": True, "orders": True})
        stats = services.filter_stats_by_permission(user, services.get_dashboard_statistics())
        self.assertIn("daily_revenue", stats)
        self.assertIn("cancelled_payments", stats)

    def test_filter_stats_by_permission_hides_everything_with_no_staffaccess_row(self):
        user = User.objects.create_user(username="noaccess1", password="pass12345")
        stats = services.filter_stats_by_permission(user, services.get_dashboard_statistics())
        self.assertEqual(stats, {})

    def test_get_statistics_for_role_was_removed(self):
        """Old role-based stat filtering must not quietly still exist underneath StaffAccess — see services.get_statistics_for_role's docstring."""
        with self.assertRaises(NotImplementedError):
            services.get_statistics_for_role("administrator")


class ChartDataServiceTests(TestCase):
    def test_revenue_chart_data_shape(self):
        data = services.get_revenue_chart_data()
        self.assertEqual(data["labels"], ["Today", "This Week", "This Month"])
        self.assertEqual(len(data["datasets"][0]["data"]), 3)

    def test_orders_chart_data_shape(self):
        data = services.get_orders_chart_data()
        self.assertEqual(data["labels"], ["Pending", "Completed"])
        self.assertEqual(len(data["datasets"][0]["data"]), 2)

    def test_tables_chart_data_shape(self):
        data = services.get_tables_chart_data()
        self.assertEqual(data["labels"], ["Available", "Occupied"])
        self.assertEqual(len(data["datasets"][0]["data"]), 2)


class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 302)

    def test_staff_without_dashboard_access_is_denied(self):
        _staff_user("nodash1", dashboard_enabled=False)
        self.client.login(username="nodash1", password="pass12345")
        response = self.client.get(reverse("dashboard:home"))
        self.assertNotEqual(response.status_code, 200)

    def test_staff_with_dashboard_access_sees_only_granted_stats(self):
        _staff_user("granted1", dashboard_enabled=True, dashboard_sections={"orders": True, "tables": True})
        self.client.login(username="granted1", password="pass12345")
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("pending_orders", response.context["stats"])
        self.assertNotIn("daily_revenue", response.context["stats"])
        self.assertNotIn("total_customers", response.context["stats"])

    def test_staff_with_payments_access_sees_revenue(self):
        _staff_user("payer1", dashboard_enabled=True, dashboard_sections={"payments": True})
        self.client.login(username="payer1", password="pass12345")
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("daily_revenue", response.context["stats"])

    def test_superuser_sees_full_stats_regardless_of_staffaccess(self):
        User.objects.create_superuser(username="root2", password="pass12345")
        self.client.login(username="root2", password="pass12345")
        response = self.client.get(reverse("dashboard:home"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context["stats"].keys()), ALL_STAT_KEYS)
