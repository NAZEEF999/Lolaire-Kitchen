"""
Tests for the inventory app.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import StaffAccess

from . import services
from .models import Ingredient, Supplier

User = get_user_model()


def _staff_user(username, **actions):
    """Creates a staff account with inventory StaffAccess — actions overrides specific view/create/edit/delete/adjust keys, defaulting the rest to False."""
    user = User.objects.create_user(username=username, password="pass12345")
    inventory_actions = {"view": False, "create": False, "edit": False, "delete": False, "adjust": False}
    inventory_actions.update(actions)
    StaffAccess.objects.create(
        user=user,
        dashboard_enabled=True,
        dashboard_sections={"inventory": True},
        dashboard_actions={"inventory": inventory_actions},
    )
    return user


class RecordStockAdjustmentServiceTests(TestCase):
    def setUp(self):
        self.ingredient = Ingredient.objects.create(name="Chicken", unit="kg", quantity_in_stock=Decimal("10.00"))

    def test_positive_adjustment_increases_stock(self):
        services.record_stock_adjustment(ingredient=self.ingredient, reason="restock", quantity_delta=Decimal("5.00"))
        self.ingredient.refresh_from_db()
        self.assertEqual(self.ingredient.quantity_in_stock, Decimal("15.00"))

    def test_negative_adjustment_within_bounds_decreases_stock(self):
        services.record_stock_adjustment(ingredient=self.ingredient, reason="usage", quantity_delta=Decimal("-4.00"))
        self.ingredient.refresh_from_db()
        self.assertEqual(self.ingredient.quantity_in_stock, Decimal("6.00"))

    def test_adjustment_that_would_go_negative_is_rejected(self):
        """Section 16 of the hardening pass — a physical stock count below zero isn't a real state, so this must raise rather than silently clamp to 0."""
        with self.assertRaises(ValidationError):
            services.record_stock_adjustment(ingredient=self.ingredient, reason="usage", quantity_delta=Decimal("-11.00"))
        self.ingredient.refresh_from_db()
        self.assertEqual(self.ingredient.quantity_in_stock, Decimal("10.00"), "Stock must be unchanged after a rejected adjustment.")

    def test_adjustment_to_exactly_zero_is_allowed(self):
        services.record_stock_adjustment(ingredient=self.ingredient, reason="usage", quantity_delta=Decimal("-10.00"))
        self.ingredient.refresh_from_db()
        self.assertEqual(self.ingredient.quantity_in_stock, Decimal("0.00"))

    def test_rejected_adjustment_does_not_create_a_history_row(self):
        try:
            services.record_stock_adjustment(ingredient=self.ingredient, reason="usage", quantity_delta=Decimal("-999.00"))
        except ValidationError:
            pass
        self.assertEqual(self.ingredient.adjustments.count(), 0)


class InventoryViewAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.ingredient = Ingredient.objects.create(name="Rice", unit="kg", quantity_in_stock=Decimal("20.00"))
        self.supplier = Supplier.objects.create(name="Acme Supplies")

        self.viewer = _staff_user("viewer1", view=True)
        self.adjuster = _staff_user("adjuster1", view=True, adjust=True)
        self.creator = _staff_user("creator1", view=True, create=True)
        self.no_access = User.objects.create_user(username="noaccess1", password="pass12345")

    def test_ingredient_list_requires_login(self):
        response = self.client.get(reverse("inventory:ingredient_list"))
        self.assertEqual(response.status_code, 302)

    def test_ingredient_list_requires_view_permission(self):
        self.client.login(username="noaccess1", password="pass12345")
        response = self.client.get(reverse("inventory:ingredient_list"))
        self.assertEqual(response.status_code, 403)

    def test_ingredient_list_accessible_with_view_permission(self):
        self.client.login(username="viewer1", password="pass12345")
        response = self.client.get(reverse("inventory:ingredient_list"))
        self.assertEqual(response.status_code, 200)

    def test_ingredient_detail_requires_view_permission(self):
        self.client.login(username="noaccess1", password="pass12345")
        response = self.client.get(reverse("inventory:ingredient_detail", args=[self.ingredient.pk]))
        self.assertEqual(response.status_code, 403)

    def test_supplier_list_requires_view_permission(self):
        """Section 15 of the hardening pass — supplier list previously only required login."""
        self.client.login(username="noaccess1", password="pass12345")
        response = self.client.get(reverse("inventory:supplier_list"))
        self.assertEqual(response.status_code, 403)

    def test_supplier_list_accessible_with_view_permission(self):
        self.client.login(username="viewer1", password="pass12345")
        response = self.client.get(reverse("inventory:supplier_list"))
        self.assertEqual(response.status_code, 200)

    def test_viewer_without_adjust_action_cannot_adjust_stock(self):
        self.client.login(username="viewer1", password="pass12345")
        response = self.client.post(
            reverse("inventory:stock_adjust", args=[self.ingredient.pk]),
            {"reason": "restock", "quantity": "5", "direction": "add", "note": ""},
        )
        self.assertEqual(response.status_code, 403)
        self.ingredient.refresh_from_db()
        self.assertEqual(self.ingredient.quantity_in_stock, Decimal("20.00"))

    def test_adjuster_can_adjust_stock(self):
        self.client.login(username="adjuster1", password="pass12345")
        response = self.client.post(
            reverse("inventory:stock_adjust", args=[self.ingredient.pk]),
            {"reason": "restock", "quantity": "5", "direction": "add", "note": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.ingredient.refresh_from_db()
        self.assertEqual(self.ingredient.quantity_in_stock, Decimal("25.00"))

    def test_adjuster_cannot_push_stock_negative_via_view(self):
        self.client.login(username="adjuster1", password="pass12345")
        response = self.client.post(
            reverse("inventory:stock_adjust", args=[self.ingredient.pk]),
            {"reason": "usage", "quantity": "999", "direction": "remove", "note": ""},
        )
        self.assertEqual(response.status_code, 302)  # Redirects back with an error message, not a 500.
        self.ingredient.refresh_from_db()
        self.assertEqual(self.ingredient.quantity_in_stock, Decimal("20.00"))

    def test_creator_without_adjust_action_cannot_adjust(self):
        self.client.login(username="creator1", password="pass12345")
        response = self.client.post(
            reverse("inventory:stock_adjust", args=[self.ingredient.pk]),
            {"reason": "restock", "quantity": "5", "direction": "add", "note": ""},
        )
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_access_everything_regardless_of_staffaccess(self):
        superuser = User.objects.create_superuser(username="root1", password="pass12345")
        self.client.login(username="root1", password="pass12345")
        response = self.client.get(reverse("inventory:ingredient_list"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("inventory:stock_adjust", args=[self.ingredient.pk]),
            {"reason": "restock", "quantity": "1", "direction": "add", "note": ""},
        )
        self.assertEqual(response.status_code, 302)
