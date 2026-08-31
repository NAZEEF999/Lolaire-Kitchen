"""
URL configuration for the storefront app — the public customer site.

Registered under app_name="storefront" and included from core/urls.py.
"""

from django.urls import path

from . import views


app_name = "storefront"


urlpatterns = [
    path(
        "",
        views.HomeView.as_view(),
        name="home",
    ),

    path(
        "about/",
        views.AboutView.as_view(),
        name="about",
    ),

    path(
        "contact/",
        views.ContactView.as_view(),
        name="contact",
    ),

    path(
        "our-menu/",
        views.PublicMenuView.as_view(),
        name="menu",
    ),

    path(
        "our-menu/<slug:slug>/",
        views.PublicMenuItemDetailView.as_view(),
        name="menu_item_detail",
    ),

    path(
        "cart/",
        views.CartView.as_view(),
        name="cart",
    ),

    path(
        "cart/add/",
        views.add_to_cart,
        name="cart_add",
    ),

    path(
        "cart/remove/<int:item_id>/",
        views.remove_from_cart,
        name="cart_remove",
    ),

    path(
        "cart/update/<int:item_id>/",
        views.update_cart_quantity,
        name="cart_update",
    ),

    path(
        "checkout/",
        views.CheckoutView.as_view(),
        name="checkout",
    ),

    path(
        "review/",
        views.ReviewCreateView.as_view(),
        name="review",
    ),

    path(
        "payments/paystack/callback/",
        views.paystack_callback,
        name="paystack_callback",
    ),

    path(
        "payments/paystack/webhook/",
        views.paystack_webhook,
        name="paystack_webhook",
    ),

    path(
        "order-confirmation/<uuid:token>/",
        views.OrderConfirmationView.as_view(),
        name="order_confirmation",
    ),

    path(
        "order-lookup/",
        views.OrderLookupView.as_view(),
        name="order_lookup",
    ),
]