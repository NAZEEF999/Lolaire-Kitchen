"""
Views for the orders app.

Per POS PREPARATION, no manual Order/OrderItem ModelForm drives order
creation — a future POS interface will create Orders/OrderItems
programmatically via services.py. These views are the backend actions
that interface will call; templates here are placeholders only.
Writes are routed through services.py so business logic stays out of
views, per the project's BUSINESS LOGIC rule.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, FormView, ListView

from accounts.permissions import has_dashboard_action
from customers.forms import CustomerForm

from . import selectors, services
from .forms import AddOrderItemForm, NewOrderForm, OrderStatusForm, PaymentStatusForm
from .models import Order, OrderItem, OrderStatus, PaymentStatus


class OrderActionRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Gates order create/edit/cancel/complete using the Staff Access
    action-level permissions (Dashboard > Staff > Manage Access) —
    these views previously had no permission check beyond being
    logged in at all, relying only on the coarser "orders" module
    toggle the middleware already enforces. Each view below sets
    `order_action` to the specific action it represents, matching
    MODULE_ACTIONS in accounts/models.py. Note this is layered on top
    of, not instead of, the separate acting_user business rule in
    orders.services (e.g. "served orders can only be edited by an
    Administrator") — that's a different, narrower rule and stays as-is.
    """

    order_action = "edit"

    def test_func(self):
        return has_dashboard_action(self.request.user, "orders", self.order_action)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class PaymentManagementRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Gates marking payments Paid/Refunded/etc using the Staff Access
    "payments: edit" action-level permission (Dashboard > Staff >
    Manage Access), replacing what used to be a hardcoded "must be
    Administrator, Manager, or Cashier" role check — a Waiter
    explicitly granted this by the Main Administrator still couldn't
    get in before this fix, and StaffAccess wasn't the actual source
    of truth despite that being the whole point of the system.
    """

    def test_func(self):
        return has_dashboard_action(self.request.user, "payments", "edit")

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class OrderListView(OrderActionRequiredMixin, ListView):
    """Searchable, filterable, paginated order list. Requires orders:view — previously only required being logged in, which meant the "View" toggle in Manage Access did nothing."""

    order_action = "view"

    template_name = "orders/order_list.html"
    context_object_name = "orders"
    paginate_by = 20

    def get_queryset(self):
        return selectors.get_orders(
            status=self.request.GET.get("status") or None,
            payment_status=self.request.GET.get("payment_status") or None,
            search=self.request.GET.get("q") or None,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_payment_status"] = self.request.GET.get("payment_status", "")
        context["status_choices"] = OrderStatus.choices
        context["payment_status_choices"] = PaymentStatus.choices
        context["can_create"] = has_dashboard_action(self.request.user, "orders", "create")
        context["can_see_payments"] = has_dashboard_action(self.request.user, "payments", "view")
        return context


class OrderDetailView(OrderActionRequiredMixin, DetailView):
    order_action = "view"
    template_name = "orders/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return selectors.get_order_detail_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["add_item_form"] = AddOrderItemForm()
        context["status_form"] = OrderStatusForm(initial={"status": self.object.status})
        context["payment_status_form"] = PaymentStatusForm(initial={"payment_status": self.object.payment_status})
        context["can_edit"] = has_dashboard_action(self.request.user, "orders", "edit")
        context["can_see_payments"] = has_dashboard_action(self.request.user, "payments", "view")
        context["can_edit_payments"] = has_dashboard_action(self.request.user, "payments", "edit")
        context["can_cancel"] = has_dashboard_action(self.request.user, "orders", "cancel")
        context["can_complete"] = has_dashboard_action(self.request.user, "orders", "complete")
        return context


class OrderCreateView(OrderActionRequiredMixin, FormView):
    """Starts a new (empty, Pending) order — items are added afterward via OrderItemAddView."""

    order_action = "create"
    form_class = NewOrderForm
    template_name = "orders/order_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Template renders an inline "quick add customer" form alongside the
        # main order form (submitted separately, via customers:create) —
        # display-only context, not part of this view's own form_valid.
        context["customer_form"] = CustomerForm()
        return context

    def form_valid(self, form):
        order = services.create_order(
            customer=form.cleaned_data["customer"],
            table=form.cleaned_data["table"],
            notes=form.cleaned_data["notes"],
            acting_user=self.request.user,
        )
        return redirect(order.get_absolute_url())


class OrderItemAddView(OrderActionRequiredMixin, View):
    order_action = "edit"

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = AddOrderItemForm(request.POST)
        if form.is_valid():
            try:
                services.add_order_item(
                    order=order,
                    menu_item=form.cleaned_data["menu_item"],
                    quantity=form.cleaned_data["quantity"],
                    notes=form.cleaned_data["notes"],
                    acting_user=request.user,
                )
                messages.success(request, "Item added.")
            except (ValidationError, PermissionDenied) as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Could not add item — check the form.")
        return redirect(order.get_absolute_url())


class OrderItemRemoveView(OrderActionRequiredMixin, View):
    order_action = "edit"

    def post(self, request, pk, item_pk):
        order = get_object_or_404(Order, pk=pk)
        item = get_object_or_404(OrderItem, pk=item_pk, order=order)
        try:
            services.remove_order_item(order_item=item, acting_user=request.user)
            messages.success(request, "Item removed.")
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        return redirect(order.get_absolute_url())


class OrderStatusUpdateView(OrderActionRequiredMixin, View):
    order_action = "edit"

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = OrderStatusForm(request.POST)
        if form.is_valid():
            try:
                services.change_order_status(
                    order=order, new_status=form.cleaned_data["status"], acting_user=request.user
                )
                messages.success(request, "Order status updated.")
            except (ValidationError, PermissionDenied) as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Invalid status selected.")
        return redirect(order.get_absolute_url())


class OrderPaymentStatusUpdateView(PaymentManagementRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = PaymentStatusForm(request.POST)
        if form.is_valid():
            services.change_payment_status(order=order, new_payment_status=form.cleaned_data["payment_status"])
            messages.success(request, "Payment status updated.")
        else:
            messages.error(request, "Invalid payment status selected.")
        return redirect(order.get_absolute_url())


class OrderCancelView(OrderActionRequiredMixin, View):
    order_action = "cancel"

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        try:
            services.cancel_order(order=order, acting_user=request.user)
            messages.success(request, "Order cancelled.")
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        return redirect(order.get_absolute_url())


class OrderCompleteView(OrderActionRequiredMixin, View):
    order_action = "complete"

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        try:
            services.complete_order(order=order, acting_user=request.user)
            messages.success(request, "Order marked served.")
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        return redirect(order.get_absolute_url())
