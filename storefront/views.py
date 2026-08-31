"""
Views for the storefront app — the public-facing customer site.

No login required anywhere here. Business logic lives in services.py;
these views stay thin.
"""

import hashlib
import hmac
import json

import requests

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, FormView, TemplateView

from menu.models import Category, MenuItem
from orders import services as order_services
from orders.models import Order, PaymentMethod, PaymentStatus

from . import selectors, services
from .forms import (
    AddToCartForm,
    CheckoutForm,
    ContactForm,
    OrderLookupForm,
    ReviewForm,
)
from .models import ContactMessage, Review
from .utils import get_cart, save_cart


def _safe_next_url(request, *, default):
    """
    Validate a caller-supplied HTTP_REFERER before redirecting.
    """
    candidate = request.META.get("HTTP_REFERER")

    if candidate and url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate

    return reverse(default)


class HomeView(TemplateView):
    template_name = "storefront/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["featured_items"] = (
            MenuItem.objects
            .filter(is_available=True)
            .select_related("category")[:6]
        )

        context["categories"] = Category.objects.all()[:6]

        context["reviews"] = (
            Review.objects
            .filter(
                is_approved=True,
                is_featured=True,
            )
            .order_by("-created_at")[:6]
        )

        return context


class PublicMenuView(TemplateView):
    template_name = "storefront/menu.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query = self.request.GET.get("q") or None
        category_slug = self.request.GET.get("category") or None

        context["menu_items"] = selectors.get_public_menu(
            category_slug=category_slug,
            search=query,
        )

        context["categories"] = selectors.get_public_categories()
        context["query"] = self.request.GET.get("q", "")
        context["selected_category"] = category_slug or ""
        context["add_to_cart_form"] = AddToCartForm

        return context


class PublicMenuItemDetailView(DetailView):
    template_name = "storefront/menu_item_detail.html"
    context_object_name = "menu_item"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            MenuItem.objects
            .filter(is_available=True)
            .select_related("category")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["related_items"] = (
            MenuItem.objects
            .filter(
                category=self.object.category,
                is_available=True,
            )
            .exclude(pk=self.object.pk)
            .select_related("category")[:3]
        )

        return context


class AboutView(TemplateView):
    template_name = "storefront/about.html"


class ContactView(FormView):
    template_name = "storefront/contact.html"
    form_class = ContactForm

    def form_valid(self, form):
        ContactMessage.objects.create(
            **form.cleaned_data
        )

        messages.success(
            self.request,
            "Thanks for reaching out — we'll get back to you soon.",
        )

        return redirect("storefront:contact")


class ReviewCreateView(FormView):
    template_name = "storefront/review_form.html"
    form_class = ReviewForm

    def form_valid(self, form):
        Review.objects.create(
            full_name=form.cleaned_data["full_name"],
            email=form.cleaned_data["email"],
            rating=form.cleaned_data["rating"],
            review=form.cleaned_data["review"],
        )

        messages.success(
            self.request,
            "Thank you for your review. It will appear after our team approves it.",
        )

        return redirect("storefront:home")


class CartView(TemplateView):
    template_name = "storefront/cart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        lines, subtotal = services.get_cart_lines(
            self.request
        )

        context["lines"] = lines
        context["subtotal"] = subtotal

        return context


def add_to_cart(request):
    if request.method == "POST":
        form = AddToCartForm(request.POST)

        if form.is_valid():
            cart = get_cart(request)

            item_id = str(
                form.cleaned_data["menu_item_id"]
            )

            quantity = form.cleaned_data["quantity"]

            cart[item_id] = (
                cart.get(item_id, 0) + quantity
            )

            save_cart(request, cart)

            messages.success(
                request,
                "Added to your cart.",
            )

        else:
            messages.error(
                request,
                "Couldn't add that item — please try again.",
            )

    return redirect(
        _safe_next_url(
            request,
            default="storefront:menu",
        )
    )


def remove_from_cart(request, item_id):
    if request.method == "POST":
        cart = get_cart(request)

        cart.pop(str(item_id), None)

        save_cart(request, cart)

        messages.success(
            request,
            "Item removed from your cart.",
        )

    return redirect("storefront:cart")


def update_cart_quantity(request, item_id):
    if request.method == "POST":
        try:
            quantity = int(
                request.POST.get("quantity", 1)
            )
        except (TypeError, ValueError):
            quantity = 1

        cart = get_cart(request)

        if quantity <= 0:
            cart.pop(str(item_id), None)
        else:
            cart[str(item_id)] = quantity

        save_cart(request, cart)

    return redirect("storefront:cart")


class CheckoutView(FormView):
    template_name = "storefront/checkout.html"
    form_class = CheckoutForm

    def get(self, request, *args, **kwargs):
        lines, _subtotal = services.get_cart_lines(
            request
        )

        if not lines:
            messages.error(
                request,
                "Your cart is empty — add something delicious first.",
            )

            return redirect("storefront:menu")

        return super().get(
            request,
            *args,
            **kwargs,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        (
            context["lines"],
            context["subtotal"],
        ) = services.get_cart_lines(
            self.request
        )

        return context

    def form_valid(self, form):
        try:
            order = services.checkout_cart(
                request=self.request,
                **form.cleaned_data,
            )

            payment = (
                services.initialize_paystack_transaction(
                    request=self.request,
                    order=order,
                    email=form.cleaned_data["email"],
                )
            )

        except ValidationError as exc:
            messages.error(
                self.request,
                str(exc),
            )

            return redirect("storefront:cart")

        except requests.RequestException as exc:
            messages.error(
                self.request,
                f"Paystack error: {exc}",
            )

            return redirect("storefront:cart")

        return redirect(
            payment["authorization_url"]
        )


def paystack_callback(request):
    """
    Paystack redirects the customer here after checkout.

    The transaction is verified server-side before the order
    is marked as paid.
    """

    reference = request.GET.get("reference")

    if not reference:
        messages.error(
            request,
            "Payment reference was not provided.",
        )

        return redirect("storefront:cart")

    try:
        transaction = (
            services.verify_paystack_transaction(
                reference=reference,
            )
        )

        if transaction.get("status") != "success":
            messages.error(
                request,
                "Payment was not successful.",
            )

            return redirect("storefront:cart")

        metadata = transaction.get("metadata") or {}

        order_id = metadata.get("order_id")

        if not order_id:
            raise ValidationError(
                "Payment is missing order information.",
            )

        order = get_object_or_404(
            Order,
            pk=order_id,
        )

        expected_amount = int(
            order.total_amount * 100
        )

        paid_amount = int(
            transaction.get("amount", 0)
        )

        if paid_amount != expected_amount:
            raise ValidationError(
                "Payment amount does not match the order.",
            )

        order_services.change_payment_status(
            order=order,
            new_payment_status=PaymentStatus.PAID,
            payment_method=PaymentMethod.ONLINE,
        )

        save_cart(request, {})

        messages.success(
            request,
            "Payment successful. Your order has been confirmed.",
        )

        return redirect(
            "storefront:order_confirmation",
            token=order.confirmation_token,
        )

    except ValidationError as exc:
        messages.error(
            request,
            str(exc),
        )

    except requests.RequestException:
        messages.error(
            request,
            "We couldn't verify the payment right now. Please try again.",
        )

    except (TypeError, ValueError):
        messages.error(
            request,
            "The payment response was invalid.",
        )

    return redirect("storefront:cart")


@csrf_exempt
def paystack_webhook(request):
    """
    Paystack webhook endpoint.

    Verifies the x-paystack-signature HMAC before processing events.
    """

    if request.method != "POST":
        return HttpResponse(status=405)

    signature = request.headers.get(
        "x-paystack-signature"
    )

    if not signature:
        return HttpResponse(status=401)

    expected_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
        request.body,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(
        signature,
        expected_signature,
    ):
        return HttpResponse(status=401)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    event = payload.get("event")

    if event == "charge.success":
        data = payload.get("data") or {}

        metadata = data.get("metadata") or {}

        order_id = metadata.get("order_id")

        if order_id:
            try:
                order = Order.objects.get(
                    pk=order_id
                )

                if (
                    order.payment_status
                    != PaymentStatus.PAID
                ):
                    order_services.change_payment_status(
                        order=order,
                        new_payment_status=PaymentStatus.PAID,
                        payment_method=PaymentMethod.ONLINE,
                    )

            except Order.DoesNotExist:
                pass

    return HttpResponse(status=200)


class OrderConfirmationView(DetailView):
    template_name = "storefront/order_confirmation.html"
    context_object_name = "order"

    def get_object(self):
        return get_object_or_404(
            (
                Order.objects
                .select_related("customer")
                .prefetch_related("items__menu_item")
            ),
            confirmation_token=self.kwargs["token"],
        )


class OrderLookupView(FormView):
    template_name = "storefront/order_lookup.html"
    form_class = OrderLookupForm

    def form_valid(self, form):
        order = selectors.get_order_for_lookup(
            phone_number=form.cleaned_data[
                "phone_number"
            ],
            order_number=form.cleaned_data[
                "order_number"
            ],
        )

        return render(
            self.request,
            self.template_name,
            {
                "form": form,
                "order": order,
                "searched": True,
            },
        )