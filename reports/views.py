"""
Views for the reports app.

Read-only. All aggregation/filtering logic lives in services.py; views
only bind GET query params to a form and pass cleaned data through.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView

from accounts.permissions import has_dashboard_action
from customers import selectors as customer_selectors

from . import services
from .forms import DateRangeForm, OrderReportFilterForm


class ReportsAccessRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Was previously hardcoded to `user.role in (ADMINISTRATOR, MANAGER)`
    — a second, independent gate that ignored the actual StaffAccess
    permission the Main Administrator controls from Dashboard > Staff.
    That meant a Cashier or Waiter explicitly granted Reports access
    still couldn't get in, and conversely wasn't quite redundant with
    accounts.middleware.StaffAccessMiddleware (which already checks
    has_dashboard_section for the /reports/ prefix) since middleware
    only gates the module as a whole — this now checks the specific
    "view" action, matching the same action-level system every other
    app in the project (menu, orders, inventory, ...) uses.
    """

    def test_func(self):
        return has_dashboard_action(self.request.user, "reports", "view")

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class ReportsHomeView(ReportsAccessRequiredMixin, TemplateView):
    template_name = "reports/home.html"


class RevenueReportView(ReportsAccessRequiredMixin, TemplateView):
    template_name = "reports/revenue_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = DateRangeForm(self.request.GET or None)
        context["form"] = form
        context["daily"] = services.get_daily_revenue_report()
        context["weekly"] = services.get_weekly_revenue_report()
        context["monthly"] = services.get_monthly_revenue_report()
        if form.is_valid() and form.cleaned_data.get("start_date") and form.cleaned_data.get("end_date"):
            context["custom_range"] = services.get_custom_range_revenue_report(
                start_date=form.cleaned_data["start_date"], end_date=form.cleaned_data["end_date"]
            )
        return context


class SalesReportView(ReportsAccessRequiredMixin, TemplateView):
    """Serves both the "Sales report" and "Menu performance report" — same underlying analytics, one view."""

    template_name = "reports/sales_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["best_selling"] = services.get_best_selling_items()
        context["least_selling"] = services.get_least_selling_items()
        context["revenue_per_item"] = services.get_revenue_per_menu_item()
        context["most_ordered_categories"] = services.get_most_ordered_categories()
        return context


class OrdersReportView(ReportsAccessRequiredMixin, TemplateView):
    template_name = "reports/orders_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = OrderReportFilterForm(self.request.GET or None)
        context["form"] = form
        context["status_breakdown"] = services.get_order_status_report()
        context["payment_status_breakdown"] = services.get_payment_status_report()
        context["payment_method_breakdown"] = services.get_payment_method_report()

        if form.is_valid() and form.cleaned_data.get("start_date") and form.cleaned_data.get("end_date"):
            context["filtered_orders"] = services.get_orders_between_report(
                start_date=form.cleaned_data["start_date"],
                end_date=form.cleaned_data["end_date"],
                status=form.cleaned_data.get("status") or None,
                payment_status=form.cleaned_data.get("payment_status") or None,
                payment_method=form.cleaned_data.get("payment_method") or None,
            )
        return context


class CustomerReportView(ReportsAccessRequiredMixin, TemplateView):
    template_name = "reports/customer_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = DateRangeForm(self.request.GET or None)
        context["form"] = form
        context["total_customers"] = services.get_total_customers_report()
        context["most_frequent_customers"] = services.get_most_frequent_customers()
        if form.is_valid() and form.cleaned_data.get("start_date") and form.cleaned_data.get("end_date"):
            context["new_customers"] = services.get_new_customers_report(
                start_date=form.cleaned_data["start_date"], end_date=form.cleaned_data["end_date"]
            )
        return context


class CustomerHistoryReportView(ReportsAccessRequiredMixin, TemplateView):
    template_name = "reports/customer_history_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = customer_selectors.get_customer_by_id(self.kwargs["customer_id"])
        context["summary"] = services.get_customer_history_summary(customer=customer) if customer else None
        return context


class TableUtilizationReportView(ReportsAccessRequiredMixin, TemplateView):
    template_name = "reports/table_utilization_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["utilization"] = services.get_table_utilization_report()
        context["most_used"] = services.get_most_used_tables()
        context["least_used"] = services.get_least_used_tables()
        return context
