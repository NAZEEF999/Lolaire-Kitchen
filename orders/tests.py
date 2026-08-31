"""
Tests for the orders app.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import StaffAccess, UserRole
from customers.models import Customer
from menu.models import Category, MenuItem
from tables.models import Table, TableStatus

from . import selectors, services
from .models import Order, OrderItem, OrderStatus, PaymentStatus
from .validators import validate_menu_item_is_active, validate_positive_quantity

User = get_user_model()


def make_menu_item(price=Decimal("1000.00"), **kwargs):
    category = Category.objects.create(name=kwargs.pop("category_name", "Mains"))
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


class OrderModelTests(TestCase):
    def test_order_number_is_auto_generated(self):
        order = Order.objects.create()
        self.assertTrue(order.order_number.startswith("ORD-"))

    def test_order_number_is_unique_even_same_day(self):
        order1 = Order.objects.create()
        order2 = Order.objects.create()
        self.assertNotEqual(order1.order_number, order2.order_number)

    def test_default_status_and_payment_status(self):
        order = Order.objects.create()
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.payment_status, PaymentStatus.PENDING)

    def test_total_amount_invariant_on_save(self):
        order = Order.objects.create(
            subtotal=Decimal("1000.00"), discount_amount=Decimal("100.00"), tax_amount=Decimal("50.00")
        )
        self.assertEqual(order.total_amount, Decimal("950.00"))

    def test_total_amount_recomputes_when_discount_changes_directly(self):
        order = Order.objects.create(subtotal=Decimal("1000.00"))
        order.discount_amount = Decimal("200.00")
        order.save()
        self.assertEqual(order.total_amount, Decimal("800.00"))

    def test_str_returns_order_number(self):
        order = Order.objects.create()
        self.assertEqual(str(order), order.order_number)

    def test_get_absolute_url(self):
        order = Order.objects.create()
        self.assertEqual(order.get_absolute_url(), f"/orders/{order.pk}/")

    def test_default_manager_excludes_inactive(self):
        active = Order.objects.create()
        inactive = Order.objects.create(is_active=False)
        self.assertIn(active, Order.objects.all())
        self.assertNotIn(inactive, Order.objects.all())
        self.assertIn(inactive, Order.all_objects.all())


class OrderQuerySetTests(TestCase):
    def setUp(self):
        self.pending = Order.objects.create(status=OrderStatus.PENDING)
        self.served = Order.objects.create(status=OrderStatus.SERVED, payment_status=PaymentStatus.PAID)
        self.cancelled = Order.objects.create(status=OrderStatus.CANCELLED)

    def test_with_status_chain(self):
        self.assertIn(self.pending, Order.objects.with_status(OrderStatus.PENDING))
        self.assertNotIn(self.served, Order.objects.with_status(OrderStatus.PENDING))

    def test_paid_and_unpaid_chain(self):
        self.assertIn(self.served, Order.objects.paid())
        self.assertIn(self.pending, Order.objects.unpaid())
        self.assertNotIn(self.served, Order.objects.unpaid())

    def test_active_chain_on_all_objects(self):
        inactive = Order.objects.create(is_active=False)
        self.assertIn(self.pending, Order.all_objects.active())
        self.assertNotIn(inactive, Order.all_objects.active())


class OrderItemModelTests(TestCase):
    def test_unit_price_snapshotted_from_menu_item_on_create(self):
        menu_item = make_menu_item(price=Decimal("1500.00"))
        order = Order.objects.create()
        item = OrderItem.objects.create(order=order, menu_item=menu_item, quantity=2)
        self.assertEqual(item.unit_price, Decimal("1500.00"))
        self.assertEqual(item.line_total, Decimal("3000.00"))

    def test_unit_price_unaffected_by_later_menu_item_price_change(self):
        menu_item = make_menu_item(price=Decimal("1000.00"))
        order = Order.objects.create()
        item = OrderItem.objects.create(order=order, menu_item=menu_item, quantity=1)

        menu_item.price = Decimal("5000.00")
        menu_item.save()

        item.refresh_from_db()
        self.assertEqual(item.unit_price, Decimal("1000.00"))

    def test_line_total_recomputes_on_quantity_update(self):
        menu_item = make_menu_item(price=Decimal("500.00"))
        order = Order.objects.create()
        item = OrderItem.objects.create(order=order, menu_item=menu_item, quantity=1)
        item.quantity = 4
        item.save()
        self.assertEqual(item.line_total, Decimal("2000.00"))
        self.assertEqual(item.unit_price, Decimal("500.00"))  # unchanged

    def test_quantity_must_be_greater_than_zero(self):
        menu_item = make_menu_item()
        order = Order.objects.create()
        item = OrderItem(order=order, menu_item=menu_item, quantity=0)
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_str_representation(self):
        menu_item = make_menu_item(name="Suya")
        order = Order.objects.create()
        item = OrderItem.objects.create(order=order, menu_item=menu_item, quantity=3)
        self.assertEqual(str(item), "3 x Suya")


class ValidatorTests(TestCase):
    def test_validate_positive_quantity_rejects_zero(self):
        with self.assertRaises(ValidationError):
            validate_positive_quantity(0)

    def test_validate_positive_quantity_accepts_positive(self):
        validate_positive_quantity(1)  # should not raise

    def test_validate_menu_item_is_active_rejects_inactive(self):
        menu_item = make_menu_item(is_active=False)
        with self.assertRaises(ValidationError):
            validate_menu_item_is_active(menu_item)

    def test_validate_menu_item_is_active_accepts_active(self):
        menu_item = make_menu_item()
        validate_menu_item_is_active(menu_item)  # should not raise


class SelectorTests(TestCase):
    def setUp(self):
        Order.objects.create(status=OrderStatus.PENDING)
        Order.objects.create(status=OrderStatus.PREPARING)
        Order.objects.create(status=OrderStatus.READY)
        Order.objects.create(status=OrderStatus.SERVED, payment_status=PaymentStatus.PAID)
        Order.objects.create(status=OrderStatus.CANCELLED)

    def test_get_pending_orders(self):
        self.assertEqual(selectors.get_pending_orders().count(), 1)

    def test_get_order_detail_queryset_returns_correct_order(self):
        target = Order.objects.first()
        found = selectors.get_order_detail_queryset().get(pk=target.pk)
        self.assertEqual(found, target)

    def test_get_preparing_orders(self):
        self.assertEqual(selectors.get_preparing_orders().count(), 1)

    def test_get_ready_orders(self):
        self.assertEqual(selectors.get_ready_orders().count(), 1)

    def test_get_served_orders(self):
        self.assertEqual(selectors.get_served_orders().count(), 1)

    def test_get_cancelled_orders(self):
        self.assertEqual(selectors.get_cancelled_orders().count(), 1)

    def test_get_unpaid_orders(self):
        self.assertEqual(selectors.get_unpaid_orders().count(), 4)

    def test_get_paid_orders(self):
        self.assertEqual(selectors.get_paid_orders().count(), 1)

    def test_get_todays_orders(self):
        self.assertEqual(selectors.get_todays_orders().count(), 5)

    def test_get_revenue_only_counts_paid(self):
        Order.objects.filter(status=OrderStatus.SERVED).update(total_amount=Decimal("2500.00"))
        self.assertEqual(selectors.get_revenue(), Decimal("2500.00"))

    def test_get_orders_search_by_order_number(self):
        order = Order.objects.first()
        results = selectors.get_orders(search=order.order_number)
        self.assertEqual(results.count(), 1)

    def test_get_order_by_number(self):
        order = Order.objects.first()
        found = selectors.get_order_by_number(order.order_number)
        self.assertEqual(found, order)

    def test_get_order_by_id(self):
        order = Order.objects.first()
        found = selectors.get_order_by_id(order.pk)
        self.assertEqual(found, order)

    def test_get_order_by_id_missing_returns_none(self):
        self.assertIsNone(selectors.get_order_by_id(999999))

    def test_get_order_history_by_customer(self):
        customer = make_customer()
        Order.objects.create(customer=customer)
        history = selectors.get_order_history(customer=customer)
        self.assertEqual(history.count(), 1)

    def test_get_order_history_by_table(self):
        table = make_table()
        Order.objects.create(table=table)
        history = selectors.get_order_history(table=table)
        self.assertEqual(history.count(), 1)


class ServiceOrderCreationTests(TestCase):
    def test_create_order_basic(self):
        order = services.create_order()
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.payment_status, PaymentStatus.PENDING)

    def test_create_order_with_table_marks_table_occupied(self):
        table = make_table()
        services.create_order(table=table)
        table.refresh_from_db()
        self.assertEqual(table.status, TableStatus.OCCUPIED)

    def test_create_order_with_customer(self):
        customer = make_customer()
        order = services.create_order(customer=customer)
        self.assertEqual(order.customer, customer)


class ServiceOrderItemTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create()
        self.menu_item = make_menu_item(price=Decimal("2000.00"))

    def test_add_order_item_snapshots_price_and_updates_totals(self):
        services.add_order_item(order=self.order, menu_item=self.menu_item, quantity=2)
        self.order.refresh_from_db()
        self.assertEqual(self.order.subtotal, Decimal("4000.00"))
        self.assertEqual(self.order.total_amount, Decimal("4000.00"))

    def test_add_order_item_rejects_inactive_menu_item(self):
        inactive_item = make_menu_item(name="Discontinued", is_active=False)
        with self.assertRaises(ValidationError):
            services.add_order_item(order=self.order, menu_item=inactive_item, quantity=1)

    def test_add_order_item_rejects_zero_quantity(self):
        with self.assertRaises(ValidationError):
            services.add_order_item(order=self.order, menu_item=self.menu_item, quantity=0)

    def test_update_order_item_recalculates_totals(self):
        item = services.add_order_item(order=self.order, menu_item=self.menu_item, quantity=1)
        services.update_order_item(order_item=item, quantity=3)
        self.order.refresh_from_db()
        self.assertEqual(self.order.subtotal, Decimal("6000.00"))

    def test_remove_order_item_recalculates_totals(self):
        item = services.add_order_item(order=self.order, menu_item=self.menu_item, quantity=1)
        services.remove_order_item(order_item=item)
        self.order.refresh_from_db()
        self.assertEqual(self.order.subtotal, Decimal("0.00"))
        self.assertFalse(OrderItem.objects.filter(pk=item.pk).exists())

    def test_calculate_totals_applies_discount_and_tax(self):
        services.add_order_item(order=self.order, menu_item=self.menu_item, quantity=1)
        self.order.discount_amount = Decimal("200.00")
        self.order.tax_amount = Decimal("100.00")
        self.order.save()
        services.calculate_totals(order=self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_amount, Decimal("1900.00"))


class ServedOrderPermissionTests(TestCase):
    """
    Rewritten for this hardening pass: editing a served order now
    requires orders:edit via StaffAccess, not the legacy `role`
    field's is_administrator check — see
    orders.services._ensure_order_is_editable's docstring.
    """

    def setUp(self):
        self.menu_item = make_menu_item(price=Decimal("1000.00"))
        self.order = Order.objects.create(status=OrderStatus.SERVED)
        self.editor = User.objects.create_user(username="editor1", password="pass12345", role=UserRole.ADMINISTRATOR)
        StaffAccess.objects.create(
            user=self.editor,
            dashboard_enabled=True,
            dashboard_sections={"orders": True},
            dashboard_actions={"orders": {"view": True, "create": True, "edit": True, "cancel": True, "complete": True}},
        )
        self.waiter = User.objects.create_user(username="waiter1", password="pass12345", role=UserRole.WAITER)
        StaffAccess.objects.create(
            user=self.waiter,
            dashboard_enabled=True,
            dashboard_sections={"orders": True},
            dashboard_actions={"orders": {"view": True, "create": True, "edit": False, "cancel": False, "complete": False}},
        )

    def test_staff_without_edit_action_cannot_add_item_to_served_order(self):
        with self.assertRaises(PermissionDenied):
            services.add_order_item(
                order=self.order, menu_item=self.menu_item, quantity=1, acting_user=self.waiter
            )

    def test_staff_with_edit_action_can_add_item_to_served_order(self):
        item = services.add_order_item(
            order=self.order, menu_item=self.menu_item, quantity=1, acting_user=self.editor
        )
        self.assertIsNotNone(item.pk)

    def test_superuser_can_add_item_to_served_order_regardless_of_staffaccess(self):
        """The Main Administrator must still have unrestricted access, per this hardening pass's explicit requirement — even with no StaffAccess row at all."""
        superuser = User.objects.create_superuser(username="root1", password="pass12345")
        item = services.add_order_item(
            order=self.order, menu_item=self.menu_item, quantity=1, acting_user=superuser
        )
        self.assertIsNotNone(item.pk)

    def test_no_acting_user_is_denied(self):
        with self.assertRaises(PermissionDenied):
            services.add_order_item(order=self.order, menu_item=self.menu_item, quantity=1)


class TableIntegrationTests(TestCase):
    def test_assign_table_marks_occupied(self):
        table = make_table()
        order = Order.objects.create()
        services.assign_table(order=order, table=table)
        table.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(table.status, TableStatus.OCCUPIED)
        self.assertEqual(order.table, table)

    def test_serving_order_releases_table(self):
        table = make_table()
        order = Order.objects.create(table=table)
        table.status = TableStatus.OCCUPIED
        table.save(update_fields=["status"])

        services.change_order_status(order=order, new_status=OrderStatus.SERVED)

        table.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(table.status, TableStatus.AVAILABLE)
        self.assertIsNone(order.table)

    def test_cancelling_order_releases_table(self):
        table = make_table()
        order = Order.objects.create(table=table)
        services.change_order_status(order=order, new_status=OrderStatus.CANCELLED)
        table.refresh_from_db()
        self.assertEqual(table.status, TableStatus.AVAILABLE)

    def test_table_not_released_if_another_active_order_still_uses_it(self):
        table = make_table()
        order1 = Order.objects.create(table=table, status=OrderStatus.PENDING)
        order2 = Order.objects.create(table=table, status=OrderStatus.SERVED)
        services.release_table(order=order2)
        table.refresh_from_db()
        # order1 is still active on this table, so it should not be freed.
        self.assertNotEqual(table.status, TableStatus.AVAILABLE)


class PaymentStatusServiceTests(TestCase):
    def test_change_payment_status(self):
        order = Order.objects.create()
        services.change_payment_status(order=order, new_payment_status=PaymentStatus.PAID)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, PaymentStatus.PAID)

    def test_change_payment_status_rejects_invalid_value(self):
        order = Order.objects.create()
        with self.assertRaises(ValidationError):
            services.change_payment_status(order=order, new_payment_status="not_a_real_status")


class CancelAndCompleteOrderTests(TestCase):
    def test_cancel_order_sets_status_and_payment(self):
        order = Order.objects.create()
        services.cancel_order(order=order)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(order.payment_status, PaymentStatus.CANCELLED)

    def test_cancel_order_does_not_touch_already_paid_payment_status(self):
        order = Order.objects.create(payment_status=PaymentStatus.PAID)
        services.cancel_order(order=order)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, PaymentStatus.PAID)

    def test_complete_order_sets_served_status(self):
        order = Order.objects.create()
        services.complete_order(order=order)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.SERVED)


class OrderViewAccessTests(TestCase):
    """
    Access decided entirely by StaffAccess now — see
    menu.tests.MenuViewAccessTests for the general rewrite reasoning.
    `full_access` has every orders action plus payments:edit;
    `limited` has orders:view/create only (matching STAFF A from the
    hardening brief's own manual-verification checklist); `no_access`
    is logged in but granted nothing.
    """

    def setUp(self):
        self.client = Client()
        self.order = Order.objects.create()

        self.full_access = User.objects.create_user(username="fullaccess1", password="pass12345", role=UserRole.ADMINISTRATOR)
        StaffAccess.objects.create(
            user=self.full_access,
            dashboard_enabled=True,
            dashboard_sections={"orders": True, "payments": True},
            dashboard_actions={
                "orders": {"view": True, "create": True, "edit": True, "cancel": True, "complete": True},
                "payments": {"view": True, "edit": True},
            },
        )

        self.limited = User.objects.create_user(username="limited1", password="pass12345", role=UserRole.WAITER)
        StaffAccess.objects.create(
            user=self.limited,
            dashboard_enabled=True,
            dashboard_sections={"orders": True},
            dashboard_actions={"orders": {"view": True, "create": True, "edit": True, "cancel": True, "complete": False}},
        )

        self.no_access = User.objects.create_user(username="noaccess1", password="pass12345", role=UserRole.WAITER)

    def test_list_requires_login(self):
        response = self.client.get(reverse("orders:list"))
        self.assertEqual(response.status_code, 302)

    def test_list_requires_orders_view_permission(self):
        """The gap Section 3 of this hardening pass closed: module ON used to be enough, View OFF (or ungranted) did nothing."""
        self.client.login(username="noaccess1", password="pass12345")
        response = self.client.get(reverse("orders:list"))
        self.assertEqual(response.status_code, 403)

    def test_list_accessible_with_view_permission(self):
        self.client.login(username="limited1", password="pass12345")
        response = self.client.get(reverse("orders:list"))
        self.assertEqual(response.status_code, 200)

    def test_detail_requires_orders_view_permission(self):
        self.client.login(username="noaccess1", password="pass12345")
        response = self.client.get(reverse("orders:detail", args=[self.order.pk]))
        self.assertEqual(response.status_code, 403)

    def test_detail_accessible_with_view_permission(self):
        self.client.login(username="limited1", password="pass12345")
        response = self.client.get(reverse("orders:detail", args=[self.order.pk]))
        self.assertEqual(response.status_code, 200)

    def test_detail_hides_payment_amounts_without_payments_view(self):
        """Section 4 of this hardening pass: Orders ON + Payments OFF must never leak totals/payment status through the Orders module."""
        self.order.subtotal = Decimal("5000.00")
        self.order.tax_amount = Decimal("250.00")
        self.order.discount_amount = Decimal("0.00")
        self.order.save()
        self.client.login(username="limited1", password="pass12345")
        response = self.client.get(reverse("orders:detail", args=[self.order.pk]))
        self.assertNotContains(response, str(self.order.total_amount))
        self.assertNotContains(response, "Subtotal")

    def test_detail_shows_payment_amounts_with_payments_view(self):
        self.client.login(username="fullaccess1", password="pass12345")
        response = self.client.get(reverse("orders:detail", args=[self.order.pk]))
        self.assertContains(response, "Subtotal")

    def test_staff_with_create_action_can_create_order(self):
        self.client.login(username="limited1", password="pass12345")
        response = self.client.post(reverse("orders:create"), {"customer": "", "table": "", "notes": ""})
        self.assertEqual(response.status_code, 302)

    def test_staff_with_edit_action_can_add_item(self):
        menu_item = make_menu_item(price=Decimal("800.00"))
        self.client.login(username="limited1", password="pass12345")
        response = self.client.post(
            reverse("orders:item_add", args=[self.order.pk]),
            {"menu_item": menu_item.pk, "quantity": 2, "notes": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(OrderItem.objects.filter(order=self.order).count(), 1)

    def test_staff_with_edit_action_can_update_order_status(self):
        self.client.login(username="limited1", password="pass12345")
        response = self.client.post(reverse("orders:status_update", args=[self.order.pk]), {"status": "preparing"})
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.PREPARING)

    def test_staff_without_payments_edit_cannot_update_payment_status(self):
        self.client.login(username="limited1", password="pass12345")
        response = self.client.post(
            reverse("orders:payment_status_update", args=[self.order.pk]), {"payment_status": "paid"}
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_with_payments_edit_can_update_payment_status(self):
        self.client.login(username="fullaccess1", password="pass12345")
        response = self.client.post(
            reverse("orders:payment_status_update", args=[self.order.pk]), {"payment_status": "paid"}
        )
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, PaymentStatus.PAID)

    def test_staff_with_cancel_action_can_cancel_order(self):
        self.client.login(username="limited1", password="pass12345")
        response = self.client.post(reverse("orders:cancel", args=[self.order.pk]))
        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.CANCELLED)

    def test_staff_without_edit_action_cannot_edit_served_order(self):
        self.order.status = OrderStatus.SERVED
        self.order.save(update_fields=["status"])
        menu_item = make_menu_item()
        no_edit_user = User.objects.create_user(username="noedit1", password="pass12345", role=UserRole.WAITER)
        StaffAccess.objects.create(
            user=no_edit_user,
            dashboard_enabled=True,
            dashboard_sections={"orders": True},
            dashboard_actions={"orders": {"view": True, "create": True, "edit": False}},
        )
        self.client.login(username="noedit1", password="pass12345")
        response = self.client.post(
            reverse("orders:item_add", args=[self.order.pk]),
            {"menu_item": menu_item.pk, "quantity": 1, "notes": ""},
        )
        # View catches PermissionDenied and redirects with an error message
        # rather than raising a hard 403, since editing a served order is a
        # recoverable user action (they just can't do it, not a security breach).
        self.assertEqual(response.status_code, 302)
        self.assertEqual(OrderItem.objects.filter(order=self.order).count(), 0)

    def test_staff_with_edit_action_can_edit_served_order(self):
        self.order.status = OrderStatus.SERVED
        self.order.save(update_fields=["status"])
        menu_item = make_menu_item()
        self.client.login(username="fullaccess1", password="pass12345")
        response = self.client.post(
            reverse("orders:item_add", args=[self.order.pk]),
            {"menu_item": menu_item.pk, "quantity": 1, "notes": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(OrderItem.objects.filter(order=self.order).count(), 1)
