"""
Tests for the reports app.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import StaffAccess, UserRole
from customers.models import Customer
from menu.models import Category, MenuItem
from orders.models import Order, OrderItem, OrderStatus, PaymentStatus
from tables.models import Table

from . import selectors, services

User = get_user_model()


def make_menu_item(price=Decimal("1000.00"), **kwargs):
    category = kwargs.pop("category", None) or Category.objects.create(name=kwargs.pop("category_name", "Mains"))
    defaults = {"category": category, "name": "Jollof Rice", "price": price}
    defaults.update(kwargs)
    return MenuItem.objects.create(**defaults)


def make_table(**kwargs):
    defaults = {"table_number": 1, "capacity": 4}
    defaults.update(kwargs)
    return Table.objects.create(**defaults)


def make_customer(**kwargs):
    defaults = {"full_name": "Ada Obi", "phone_number": "08012345678"}
    defaults.update(kwargs)
    return Customer.objects.create(**defaults)


def make_paid_order(*, total, **kwargs):
    order = Order.objects.create(status=OrderStatus.SERVED, payment_status=PaymentStatus.PAID, **kwargs)
    order.subtotal = total
    order.save(update_fields=["subtotal", "total_amount"])
    return order


class RevenueSelectorTests(TestCase):
    def test_get_revenue_between_sums_only_paid_orders(self):
        make_paid_order(total=Decimal("1000.00"))
        Order.objects.create(status=OrderStatus.PENDING)  # unpaid, should not count
        today = timezone.localdate()
        self.assertEqual(selectors.get_revenue_between(today, today), Decimal("1000.00"))

    def test_get_revenue_between_excludes_outside_range(self):
        order = make_paid_order(total=Decimal("500.00"))
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(days=10))
        today = timezone.localdate()
        self.assertEqual(selectors.get_revenue_between(today, today), 0)

    def test_get_revenue_between_includes_start_and_end_boundaries(self):
        make_paid_order(total=Decimal("300.00"))
        today = timezone.localdate()
        self.assertEqual(selectors.get_revenue_between(today - timedelta(days=1), today), Decimal("300.00"))


class OrderBreakdownSelectorTests(TestCase):
    def setUp(self):
        Order.objects.create(status=OrderStatus.PENDING, payment_status=PaymentStatus.PENDING)
        Order.objects.create(status=OrderStatus.SERVED, payment_status=PaymentStatus.PAID, payment_method="cash")
        Order.objects.create(status=OrderStatus.SERVED, payment_status=PaymentStatus.PAID, payment_method="cash")
        Order.objects.create(status=OrderStatus.CANCELLED, payment_status=PaymentStatus.CANCELLED)

    def test_status_breakdown_counts(self):
        breakdown = {row["status"]: row["count"] for row in selectors.get_order_status_breakdown()}
        self.assertEqual(breakdown.get("pending"), 1)
        self.assertEqual(breakdown.get("served"), 2)
        self.assertEqual(breakdown.get("cancelled"), 1)

    def test_payment_status_breakdown_counts(self):
        breakdown = {row["payment_status"]: row["count"] for row in selectors.get_payment_status_breakdown()}
        self.assertEqual(breakdown.get("paid"), 2)

    def test_payment_method_breakdown_excludes_blank(self):
        breakdown = {row["payment_method"]: row["count"] for row in selectors.get_payment_method_breakdown()}
        self.assertEqual(breakdown.get("cash"), 2)
        self.assertNotIn("", breakdown)

    def test_get_orders_between(self):
        today = timezone.localdate()
        self.assertEqual(selectors.get_orders_between(today, today).count(), 4)


class MenuAnalyticsSelectorTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Mains")
        self.item_a = make_menu_item(category=self.category, name="Jollof Rice", price=Decimal("1000.00"))
        self.item_b = make_menu_item(category=self.category, name="Fried Rice", price=Decimal("1200.00"))

        served_order = Order.objects.create(status=OrderStatus.SERVED)
        OrderItem.objects.create(order=served_order, menu_item=self.item_a, quantity=5)

        cancelled_order = Order.objects.create(status=OrderStatus.CANCELLED)
        OrderItem.objects.create(order=cancelled_order, menu_item=self.item_b, quantity=10)

    def test_menu_item_sales_excludes_cancelled_orders(self):
        sales = {item.pk: item.units_sold for item in selectors.get_menu_item_sales()}
        self.assertEqual(sales[self.item_a.pk], 5)
        self.assertIsNone(sales[self.item_b.pk])  # only sold via the cancelled order

    def test_category_order_volume_excludes_cancelled_orders(self):
        volume = {c.pk: c.units_ordered for c in selectors.get_category_order_volume()}
        self.assertEqual(volume[self.category.pk], 5)

    def test_menu_item_sales_excludes_inactive_order(self):
        served_order = Order.objects.create(status=OrderStatus.SERVED, is_active=False)
        OrderItem.objects.create(order=served_order, menu_item=self.item_a, quantity=100)
        sales = {item.pk: item.units_sold for item in selectors.get_menu_item_sales()}
        self.assertEqual(sales[self.item_a.pk], 5)  # unaffected by the soft-deleted order


class CustomerTableSelectorTests(TestCase):
    def test_new_customers_between(self):
        make_customer(full_name="In Range", phone_number="08011111111")
        today = timezone.localdate()
        self.assertEqual(selectors.get_new_customers_between(today, today).count(), 1)

    def test_customer_order_frequency_excludes_inactive_orders(self):
        customer = make_customer()
        Order.objects.create(customer=customer)
        Order.objects.create(customer=customer, is_active=False)
        frequency = {c.pk: c.order_count for c in selectors.get_customer_order_frequency()}
        self.assertEqual(frequency[customer.pk], 1)

    def test_table_utilization_excludes_inactive_orders(self):
        table = make_table()
        Order.objects.create(table=table)
        Order.objects.create(table=table, is_active=False)
        utilization = {t.pk: t.order_count for t in selectors.get_table_utilization()}
        self.assertEqual(utilization[table.pk], 1)


class RevenueServiceTests(TestCase):
    def test_daily_revenue_report_reuses_orders_selector(self):
        make_paid_order(total=Decimal("750.00"))
        report = services.get_daily_revenue_report()
        self.assertEqual(report["revenue"], Decimal("750.00"))
        self.assertEqual(report["period"], "Today")

    def test_weekly_and_monthly_reports_include_todays_revenue(self):
        make_paid_order(total=Decimal("400.00"))
        self.assertEqual(services.get_weekly_revenue_report()["revenue"], Decimal("400.00"))
        self.assertEqual(services.get_monthly_revenue_report()["revenue"], Decimal("400.00"))

    def test_custom_range_revenue_report(self):
        make_paid_order(total=Decimal("200.00"))
        today = timezone.localdate()
        report = services.get_custom_range_revenue_report(start_date=today, end_date=today)
        self.assertEqual(report["revenue"], Decimal("200.00"))


class SalesServiceTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Mains")
        self.popular = make_menu_item(category=self.category, name="Popular Item", price=Decimal("1000.00"))
        self.unpopular = make_menu_item(category=self.category, name="Unpopular Item", price=Decimal("500.00"))
        order = Order.objects.create(status=OrderStatus.SERVED)
        OrderItem.objects.create(order=order, menu_item=self.popular, quantity=20)
        OrderItem.objects.create(order=order, menu_item=self.unpopular, quantity=1)

    def test_best_selling_items_ordering(self):
        best = services.get_best_selling_items()
        self.assertEqual(best[0].pk, self.popular.pk)

    def test_least_selling_items_ordering(self):
        least = services.get_least_selling_items()
        self.assertEqual(least[0].pk, self.unpopular.pk)

    def test_revenue_per_menu_item(self):
        revenue = {item.pk: item.item_revenue for item in services.get_revenue_per_menu_item()}
        self.assertEqual(revenue[self.popular.pk], Decimal("20000.00"))

    def test_most_ordered_categories(self):
        categories = services.get_most_ordered_categories()
        self.assertEqual(categories[0].pk, self.category.pk)
        self.assertEqual(categories[0].units_ordered, 21)


class OrdersServiceTests(TestCase):
    def test_get_order_status_report_has_labels(self):
        Order.objects.create(status=OrderStatus.PENDING)
        report = services.get_order_status_report()
        pending_row = next(row for row in report if row["status"] == "pending")
        self.assertEqual(pending_row["label"], "Pending")
        self.assertEqual(pending_row["count"], 1)

    def test_orders_between_report_applies_all_filters(self):
        today = timezone.localdate()
        Order.objects.create(status=OrderStatus.SERVED, payment_status=PaymentStatus.PAID, payment_method="cash")
        Order.objects.create(status=OrderStatus.PENDING, payment_status=PaymentStatus.PENDING)
        results = services.get_orders_between_report(
            start_date=today, end_date=today, status=OrderStatus.SERVED, payment_status=PaymentStatus.PAID
        )
        self.assertEqual(results.count(), 1)

    def test_get_payment_status_report_has_labels(self):
        Order.objects.create(payment_status=PaymentStatus.PAID)
        report = services.get_payment_status_report()
        paid_row = next(row for row in report if row["payment_status"] == "paid")
        self.assertEqual(paid_row["label"], "Paid")
        self.assertEqual(paid_row["count"], 1)

    def test_get_payment_method_report_has_labels(self):
        Order.objects.create(payment_method="cash")
        Order.objects.create(payment_method="cash")
        report = services.get_payment_method_report()
        cash_row = next(row for row in report if row["payment_method"] == "cash")
        self.assertEqual(cash_row["label"], "Cash")
        self.assertEqual(cash_row["count"], 2)


class CustomerServiceTests(TestCase):
    def test_total_customers_report_reuses_customers_selector(self):
        make_customer()
        make_customer(full_name="Second", phone_number="08099999999")
        self.assertEqual(services.get_total_customers_report(), 2)

    def test_most_frequent_customers(self):
        frequent = make_customer(full_name="Frequent", phone_number="08011112222")
        rare = make_customer(full_name="Rare", phone_number="08033334444")
        Order.objects.create(customer=frequent)
        Order.objects.create(customer=frequent)
        Order.objects.create(customer=rare)
        result = services.get_most_frequent_customers()
        self.assertEqual(result[0].pk, frequent.pk)
        self.assertEqual(result[0].order_count, 2)

    def test_customer_history_summary_reuses_order_history_selector(self):
        customer = make_customer()
        make_paid_order(total=Decimal("500.00"), customer=customer)
        make_paid_order(total=Decimal("300.00"), customer=customer)
        summary = services.get_customer_history_summary(customer=customer)
        self.assertEqual(summary["order_count"], 2)
        self.assertEqual(summary["total_spent"], Decimal("800.00"))

    def test_get_new_customers_report(self):
        make_customer(full_name="Fresh Face", phone_number="08055556666")
        today = timezone.localdate()
        result = services.get_new_customers_report(start_date=today, end_date=today)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().full_name, "Fresh Face")


class TableServiceTests(TestCase):
    def test_most_and_least_used_tables(self):
        busy = make_table(table_number=1)
        quiet = make_table(table_number=2)
        Order.objects.create(table=busy)
        Order.objects.create(table=busy)
        Order.objects.create(table=quiet)
        most_used = services.get_most_used_tables()
        self.assertEqual(most_used[0].pk, busy.pk)
        least_used = services.get_least_used_tables()
        self.assertEqual(least_used[0].order_count, 0)  # unused tables sort first

    def test_get_table_utilization_report_orders_by_usage_descending(self):
        busy = make_table(table_number=3)
        quiet = make_table(table_number=4)
        Order.objects.create(table=busy)
        Order.objects.create(table=busy)
        Order.objects.create(table=quiet)
        report = list(services.get_table_utilization_report())
        self.assertEqual(report[0].pk, busy.pk)
        self.assertEqual(report[0].order_count, 2)


class ReportsPermissionTests(TestCase):
    """
    Access decided entirely by StaffAccess now — reports:view was
    already fixed to use has_dashboard_action before this hardening
    pass began (see reports/views.py's ReportsAccessRequiredMixin
    docstring), but this test file was never updated to match. Rank
    fixtures below are kept only as inert identity metadata.
    """

    def setUp(self):
        self.client = Client()
        self.granted = User.objects.create_user(username="granted1", password="pass12345", role=UserRole.ADMINISTRATOR)
        StaffAccess.objects.create(
            user=self.granted,
            dashboard_enabled=True,
            dashboard_sections={"reports": True},
            dashboard_actions={"reports": {"view": True}},
        )
        self.no_access = User.objects.create_user(username="noaccess1", password="pass12345", role=UserRole.WAITER)

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("reports:home"))
        self.assertEqual(response.status_code, 302)

    def test_staff_with_reports_view_can_access(self):
        self.client.login(username="granted1", password="pass12345")
        response = self.client.get(reverse("reports:home"))
        self.assertEqual(response.status_code, 200)

    def test_staff_without_reports_view_cannot_access(self):
        self.client.login(username="noaccess1", password="pass12345")
        response = self.client.get(reverse("reports:home"))
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_access_regardless_of_staffaccess(self):
        superuser = User.objects.create_superuser(username="root1", password="pass12345")
        self.client.login(username="root1", password="pass12345")
        response = self.client.get(reverse("reports:home"))
        self.assertEqual(response.status_code, 200)

    def test_staff_without_reports_view_cannot_access_every_report_view(self):
        self.client.login(username="noaccess1", password="pass12345")
        for name, kwargs in [
            ("reports:revenue", {}),
            ("reports:sales", {}),
            ("reports:menu_performance", {}),
            ("reports:orders", {}),
            ("reports:customers", {}),
            ("reports:tables", {}),
        ]:
            response = self.client.get(reverse(name, kwargs=kwargs))
            self.assertEqual(response.status_code, 403, f"{name} should be forbidden without reports:view")


class ReportsViewRenderTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin1", password="pass12345", role=UserRole.ADMINISTRATOR)
        StaffAccess.objects.create(
            user=self.admin,
            dashboard_enabled=True,
            dashboard_sections={"reports": True},
            dashboard_actions={"reports": {"view": True}},
        )
        self.client.login(username="admin1", password="pass12345")

    def test_revenue_report_renders(self):
        response = self.client.get(reverse("reports:revenue"))
        self.assertEqual(response.status_code, 200)

    def test_revenue_report_custom_range(self):
        make_paid_order(total=Decimal("100.00"))
        today = timezone.localdate()
        response = self.client.get(reverse("reports:revenue"), {"start_date": today, "end_date": today})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["custom_range"]["revenue"], Decimal("100.00"))

    def test_sales_report_renders(self):
        response = self.client.get(reverse("reports:sales"))
        self.assertEqual(response.status_code, 200)

    def test_menu_performance_alias_renders_same_view(self):
        response = self.client.get(reverse("reports:menu_performance"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reports/sales_report.html")

    def test_orders_report_renders(self):
        response = self.client.get(reverse("reports:orders"))
        self.assertEqual(response.status_code, 200)

    def test_customer_report_renders(self):
        response = self.client.get(reverse("reports:customers"))
        self.assertEqual(response.status_code, 200)

    def test_customer_history_report_renders_for_valid_customer(self):
        customer = make_customer()
        response = self.client.get(reverse("reports:customer_history", args=[customer.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["summary"])

    def test_customer_history_report_handles_missing_customer(self):
        response = self.client.get(reverse("reports:customer_history", args=[99999]))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["summary"])

    def test_table_utilization_report_renders(self):
        response = self.client.get(reverse("reports:tables"))
        self.assertEqual(response.status_code, 200)

    def test_date_range_form_rejects_start_after_end(self):
        today = timezone.localdate()
        response = self.client.get(
            reverse("reports:revenue"), {"start_date": today, "end_date": today - timedelta(days=1)}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["form"].is_valid())
        self.assertNotIn("custom_range", response.context)
