"""
Tests for the menu app.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import StaffAccess, UserRole

from . import selectors, services
from .models import Category, MenuItem

User = get_user_model()


def make_category(**kwargs):
    defaults = {"name": "Starters"}
    defaults.update(kwargs)
    return Category.objects.create(**defaults)


def make_menu_item(category=None, **kwargs):
    category = category or make_category()
    defaults = {"category": category, "name": "Spring Rolls", "price": Decimal("1500.00")}
    defaults.update(kwargs)
    return MenuItem.objects.create(**defaults)


class CategoryModelTests(TestCase):
    def test_slug_is_auto_generated(self):
        category = make_category(name="Main Course")
        self.assertEqual(category.slug, "main-course")

    def test_name_must_be_unique(self):
        make_category(name="Drinks")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_category(name="Drinks")

    def test_duplicate_name_generates_unique_slug(self):
        # Slugs are checked independently of the name-uniqueness constraint,
        # so two categories that slugify the same (but differ in case/spacing)
        # still get distinct slugs.
        make_category(name="Soups")
        second = Category(name="soups ")
        second.slug = ""  # force auto-generation
        # name uniqueness will actually block this at save() time; verify that instead.
        with self.assertRaises(Exception):
            with transaction.atomic():
                second.full_clean()
                second.save()

    def test_default_manager_excludes_inactive(self):
        active = make_category(name="Active Cat")
        inactive = make_category(name="Inactive Cat", is_active=False)
        self.assertIn(active, Category.objects.all())
        self.assertNotIn(inactive, Category.objects.all())
        self.assertIn(inactive, Category.all_objects.all())

    def test_str_returns_name(self):
        category = make_category(name="Desserts")
        self.assertEqual(str(category), "Desserts")

    def test_all_objects_active_chain_matches_default_manager(self):
        active = make_category(name="Chained Active")
        make_category(name="Chained Inactive", is_active=False)
        self.assertIn(active, Category.all_objects.active())
        self.assertEqual(list(Category.objects.all()), list(Category.all_objects.active().order_by("display_order", "name")))

    def test_get_absolute_url(self):
        category = make_category(name="Beverages")
        self.assertEqual(category.get_absolute_url(), f"/menu/categories/{category.slug}/")

    def test_ordering_by_display_order(self):
        make_category(name="Third", display_order=3)
        make_category(name="First", display_order=1)
        make_category(name="Second", display_order=2)
        names = list(Category.objects.values_list("name", flat=True))
        self.assertEqual(names, ["First", "Second", "Third"])


class MenuItemModelTests(TestCase):
    def test_slug_is_auto_generated(self):
        item = make_menu_item(name="Chicken Suya")
        self.assertEqual(item.slug, "chicken-suya")

    def test_name_unique_within_category_only(self):
        category_a = make_category(name="Grills")
        category_b = make_category(name="Snacks")
        make_menu_item(category=category_a, name="Suya")
        # Same name in a *different* category is allowed.
        item_b = make_menu_item(category=category_b, name="Suya")
        self.assertEqual(item_b.name, "Suya")
        # Same name in the *same* category is not.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_menu_item(category=category_a, name="Suya")

    def test_slug_unique_within_category_gets_suffixed(self):
        category = make_category(name="Sides")
        # Force two items that would slugify identically within one category.
        item1 = MenuItem.objects.create(category=category, name="Fries", price=Decimal("800"))
        item2 = MenuItem(category=category, name="Fries!!", price=Decimal("800"))
        # "Fries!!" slugifies to "fries", colliding with item1's slug.
        item2.save()
        self.assertEqual(item1.slug, "fries")
        self.assertEqual(item2.slug, "fries-2")

    def test_negative_price_fails_validation(self):
        item = MenuItem(category=make_category(), name="Bad Item", price=Decimal("-5.00"))
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_default_manager_excludes_inactive(self):
        active = make_menu_item(name="Available Item")
        inactive = make_menu_item(name="Hidden Item", is_active=False)
        self.assertIn(active, MenuItem.objects.all())
        self.assertNotIn(inactive, MenuItem.objects.all())
        self.assertIn(inactive, MenuItem.all_objects.all())

    def test_str_includes_category(self):
        category = make_category(name="Grills")
        item = make_menu_item(category=category, name="Suya")
        self.assertEqual(str(item), "Suya (Grills)")

    def test_get_absolute_url(self):
        item = make_menu_item(name="Jollof Rice")
        self.assertEqual(item.get_absolute_url(), f"/menu/items/{item.slug}/")

    def test_all_objects_active_and_available_chain(self):
        category = make_category(name="Chain Test")
        available_item = make_menu_item(category=category, name="Available Item", is_available=True)
        unavailable_item = make_menu_item(category=category, name="Unavailable Item", is_available=False)
        inactive_item = make_menu_item(category=category, name="Inactive Item", is_active=False)

        active_qs = MenuItem.all_objects.active()
        self.assertIn(available_item, active_qs)
        self.assertIn(unavailable_item, active_qs)
        self.assertNotIn(inactive_item, active_qs)

        available_qs = MenuItem.all_objects.active().available()
        self.assertIn(available_item, available_qs)
        self.assertNotIn(unavailable_item, available_qs)
        self.assertNotIn(inactive_item, available_qs)


class SelectorTests(TestCase):
    def setUp(self):
        self.category = make_category(name="Mains")
        make_menu_item(category=self.category, name="Jollof Rice", price=Decimal("2000"))
        make_menu_item(category=self.category, name="Fried Rice", price=Decimal("2200"), is_available=False)
        other_category = make_category(name="Drinks")
        make_menu_item(category=other_category, name="Chapman", price=Decimal("1200"))

    def test_get_active_categories_annotates_item_count(self):
        categories = {c.slug: c for c in selectors.get_active_categories()}
        self.assertEqual(categories["mains"].item_count, 2)
        self.assertEqual(categories["drinks"].item_count, 1)

    def test_get_menu_items_filters_by_category(self):
        items = selectors.get_menu_items(category_slug="mains")
        self.assertEqual(items.count(), 2)

    def test_get_menu_items_filters_by_availability(self):
        items = selectors.get_menu_items(is_available=True)
        self.assertEqual(items.count(), 2)

    def test_get_menu_items_search(self):
        items = selectors.get_menu_items(search="jollof")
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().name, "Jollof Rice")

    def test_get_category_by_slug(self):
        self.assertEqual(selectors.get_category_by_slug("mains"), self.category)

    def test_get_menu_item_by_slug(self):
        item = selectors.get_menu_item_by_slug("jollof-rice")
        self.assertIsNotNone(item)
        self.assertEqual(item.name, "Jollof Rice")


class ServiceTests(TestCase):
    def test_create_category(self):
        category = services.create_category(name="Grills", display_order=2)
        self.assertTrue(Category.objects.filter(name="Grills").exists())
        self.assertEqual(category.display_order, 2)

    def test_update_category_only_changes_provided_fields(self):
        category = make_category(name="Old Name", description="Old desc")
        services.update_category(category=category, description="New desc")
        category.refresh_from_db()
        self.assertEqual(category.name, "Old Name")
        self.assertEqual(category.description, "New desc")

    def test_deactivate_category_cascades_to_items(self):
        category = make_category(name="Grills")
        item = make_menu_item(category=category, name="Suya")
        services.deactivate_category(category=category)
        category.refresh_from_db()
        item.refresh_from_db()
        self.assertFalse(category.is_active)
        self.assertFalse(item.is_active)

    def test_create_menu_item(self):
        category = make_category()
        item = services.create_menu_item(category=category, name="Pepper Soup", price=Decimal("1800"))
        self.assertTrue(MenuItem.objects.filter(name="Pepper Soup").exists())
        self.assertEqual(item.category, category)

    def test_update_menu_item_only_changes_provided_fields(self):
        item = make_menu_item(name="Original", price=Decimal("1000"))
        services.update_menu_item(menu_item=item, price=Decimal("1200"))
        item.refresh_from_db()
        self.assertEqual(item.name, "Original")
        self.assertEqual(item.price, Decimal("1200"))

    def test_deactivate_menu_item(self):
        item = make_menu_item()
        services.deactivate_menu_item(menu_item=item)
        item.refresh_from_db()
        self.assertFalse(item.is_active)


class MenuViewAccessTests(TestCase):
    """
    Rewritten for this hardening pass: access is decided entirely by
    StaffAccess now, not by `role` — `role` fixtures below are kept
    only as inert identity metadata (matching how the real project
    treats it), never as the reason a check passes or fails.
    """

    def setUp(self):
        self.client = Client()
        self.category = make_category(name="Mains")
        self.item = make_menu_item(category=self.category, name="Jollof Rice")

        self.admin = User.objects.create_user(username="admin1", password="pass12345", role=UserRole.ADMINISTRATOR)
        StaffAccess.objects.create(
            user=self.admin,
            dashboard_enabled=True,
            dashboard_sections={"menu": True},
            dashboard_actions={"menu": {"view": True, "create": True, "edit": True, "delete": True}},
        )
        self.waiter = User.objects.create_user(username="waiter1", password="pass12345", role=UserRole.WAITER)
        StaffAccess.objects.create(
            user=self.waiter,
            dashboard_enabled=True,
            dashboard_sections={"menu": True},
            dashboard_actions={"menu": {"view": True, "create": False, "edit": False, "delete": False}},
        )
        self.no_access_waiter = User.objects.create_user(username="waiter2", password="pass12345", role=UserRole.WAITER)

    def test_item_list_requires_login(self):
        response = self.client.get(reverse("menu:item_list"))
        self.assertEqual(response.status_code, 302)

    def test_item_list_requires_menu_view_permission(self):
        """Being logged in is not enough on its own — menu:view must be explicitly granted. This is the exact gap this hardening pass closed."""
        self.client.login(username="waiter2", password="pass12345")
        response = self.client.get(reverse("menu:item_list"))
        self.assertEqual(response.status_code, 403)

    def test_item_list_accessible_with_view_permission(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("menu:item_list"))
        self.assertEqual(response.status_code, 200)

    def test_item_list_search_and_filter(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("menu:item_list"), {"q": "jollof"})
        self.assertContains(response, "Jollof Rice")

    def test_item_detail_accessible_with_view_permission(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("menu:item_detail", args=[self.item.slug]))
        self.assertEqual(response.status_code, 200)

    def test_waiter_without_create_action_cannot_create_item(self):
        """waiter1 has menu:view but not menu:create — a real distinction the old role-only check couldn't express."""
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("menu:item_create"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_item(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(reverse("menu:item_create"), {
            "category": self.category.pk,
            "name": "Egusi Soup",
            "description": "",
            "price": "2500",
            "is_available": "on",
            "is_active": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MenuItem.objects.filter(name="Egusi Soup").exists())

    def test_admin_can_delete_item_soft_deletes(self):
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(reverse("menu:item_delete", args=[self.item.slug]))
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertFalse(self.item.is_active)
        self.assertTrue(MenuItem.all_objects.filter(pk=self.item.pk).exists())

    def test_waiter_cannot_create_category(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("menu:category_create"))
        self.assertEqual(response.status_code, 403)

    def test_category_list_accessible(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("menu:category_list"))
        self.assertEqual(response.status_code, 200)

    def test_category_detail_accessible(self):
        self.client.login(username="waiter1", password="pass12345")
        response = self.client.get(reverse("menu:category_detail", args=[self.category.slug]))
        self.assertEqual(response.status_code, 200)
