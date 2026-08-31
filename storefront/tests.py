"""
Tests for the storefront app.

Given the delivery timeline, coverage here is intentionally lighter
than the rest of the project (which has comprehensive suites) — the
highest-value path (checkout creates a real Order) is covered; a full
pass matching the rest of the project's test depth is a follow-up.
Reservation tests live in the `reservations` app instead, since that
app now owns the Reservation model.
"""

from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from menu.models import Category, MenuItem
from orders.models import Order


def make_menu_item(**kwargs):
    category = Category.objects.create(name=kwargs.pop("category_name", "Mains"))
    defaults = {"category": category, "name": "Jollof Rice", "price": Decimal("2500.00")}
    defaults.update(kwargs)
    return MenuItem.objects.create(**defaults)


class PublicPagesTests(TestCase):
    def test_home_loads(self):
        response = Client().get(reverse("storefront:home"))
        self.assertEqual(response.status_code, 200)

    def test_menu_loads_and_lists_available_items(self):
        make_menu_item(name="Jollof Rice")
        response = Client().get(reverse("storefront:menu"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jollof Rice")

    def test_menu_item_detail_loads(self):
        item = make_menu_item()
        response = Client().get(reverse("storefront:menu_item_detail", args=[item.slug]))
        self.assertEqual(response.status_code, 200)

    def test_about_and_contact_load(self):
        client = Client()
        self.assertEqual(client.get(reverse("storefront:about")).status_code, 200)
        self.assertEqual(client.get(reverse("storefront:contact")).status_code, 200)


class CartAndCheckoutTests(TestCase):
    def test_add_to_cart_and_checkout_creates_real_order(self):
        item = make_menu_item(price=Decimal("1500.00"))
        client = Client()
        client.post(reverse("storefront:cart_add"), {"menu_item_id": item.pk, "quantity": 2})

        response = client.post(reverse("storefront:checkout"), {
            "full_name": "Ada Obi",
            "phone_number": "08012345678",
            "email": "",
            "delivery_address": "12 Marina Road",
            "notes": "",
        })
        self.assertEqual(response.status_code, 302)
        order = Order.objects.first()
        self.assertIsNotNone(order)
        self.assertEqual(order.subtotal, Decimal("3000.00"))
        self.assertEqual(order.customer.full_name, "Ada Obi")

    def test_checkout_with_empty_cart_redirects_to_menu(self):
        response = Client().get(reverse("storefront:checkout"))
        self.assertRedirects(response, reverse("storefront:menu"))
