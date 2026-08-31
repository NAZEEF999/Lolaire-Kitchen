"""
Views for the customers app.

Uses Django's generic class-based views. Writes are routed through
services.py (not form.save()/self.object.delete()) so business logic
stays out of views, per the project's BUSINESS LOGIC rule. Pagination
is Django's built-in ListView.paginate_by.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.permissions import has_dashboard_action

from . import selectors, services
from .forms import CustomerForm
from .models import Customer


class StaffManagementRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Gates create/edit/delete of customer records using the Staff
    Access action-level permissions (Dashboard > Staff > Manage
    Access), replacing what used to be a hardcoded "must be
    Administrator or Manager" check that ignored StaffAccess entirely.
    Each view below sets `customers_action` to the specific action it
    represents, matching MODULE_ACTIONS in accounts/models.py.
    """

    customers_action = "edit"

    def test_func(self):
        return has_dashboard_action(self.request.user, "customers", self.customers_action)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class CustomerListView(StaffManagementRequiredMixin, ListView):
    customers_action = "view"
    """Searchable, paginated customer list."""

    template_name = "customers/customer_list.html"
    context_object_name = "customers"
    paginate_by = 15

    def get_queryset(self):
        return selectors.get_customers(search=self.request.GET.get("q") or None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "")
        context["can_create"] = has_dashboard_action(self.request.user, "customers", "create")
        return context


class CustomerDetailView(StaffManagementRequiredMixin, DetailView):
    customers_action = "view"
    template_name = "customers/customer_detail.html"
    context_object_name = "customer"

    def get_queryset(self):
        return Customer.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["order_history"] = selectors.get_order_history(self.object)
        context["can_edit"] = has_dashboard_action(self.request.user, "customers", "edit")
        context["can_delete"] = has_dashboard_action(self.request.user, "customers", "delete")
        return context


class CustomerCreateView(StaffManagementRequiredMixin, CreateView):
    customers_action = "create"
    form_class = CustomerForm
    template_name = "customers/customer_form.html"
    success_url = reverse_lazy("customers:list")

    def form_valid(self, form):
        self.object = services.create_customer(**form.cleaned_data)
        return redirect(self.get_success_url())


class CustomerUpdateView(StaffManagementRequiredMixin, UpdateView):
    form_class = CustomerForm
    template_name = "customers/customer_form.html"
    success_url = reverse_lazy("customers:list")

    def get_queryset(self):
        return Customer.objects.all()

    def form_valid(self, form):
        self.object = services.update_customer(customer=self.object, **form.cleaned_data)
        return redirect(self.get_success_url())


class CustomerDeleteView(StaffManagementRequiredMixin, DeleteView):
    customers_action = "delete"
    template_name = "customers/customer_confirm_delete.html"
    success_url = reverse_lazy("customers:list")

    def get_queryset(self):
        return Customer.objects.all()

    def form_valid(self, form):
        """Soft-delete via services.py instead of a real DB delete."""
        services.deactivate_customer(customer=self.object)
        return redirect(self.get_success_url())
