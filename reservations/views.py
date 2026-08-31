"""
Views for the reservations app.

Public-facing:
- Anyone can submit a reservation request.

Dashboard:
- Authorized staff can view reservations.
- Authorized staff can change reservation status directly
  from the normal Lolaire's Kitchen dashboard.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView

from accounts.permissions import has_dashboard_action

from .forms import ReservationForm
from .models import Reservation, ReservationStatus


class ReservationCreateView(CreateView):
    """
    Public reservation form.
    No login required.
    """

    form_class = ReservationForm
    template_name = "reservations/reservation_form.html"
    success_url = reverse_lazy("reservations:success")

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            "Your table request has been received — "
            "we'll confirm it by phone or email shortly.",
        )

        return response


class ReservationSuccessView(TemplateView):
    """
    Public reservation success page.
    """

    template_name = "reservations/reservation_success.html"


class ReservationListView(
    LoginRequiredMixin,
    UserPassesTestMixin,
    ListView,
):
    """
    Staff dashboard reservation list.

    Requires the reservations:view dashboard permission.
    """

    template_name = "reservations/manage_list.html"
    context_object_name = "reservations"
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            Reservation.objects
            .select_related()
            .order_by(
                "-reservation_date",
                "-reservation_time",
            )
        )

        status = self.request.GET.get("status")

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["selected_status"] = self.request.GET.get(
            "status",
            "",
        )

        context["status_choices"] = (
            Reservation._meta
            .get_field("status")
            .choices
        )

        return context

    def test_func(self):
        return has_dashboard_action(
            self.request.user,
            "reservations",
            "view",
        )

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied

        return super().handle_no_permission()


class ReservationStatusUpdateView(
    LoginRequiredMixin,
    UserPassesTestMixin,
    View,
):
    """
    Change a reservation's status directly from the
    normal restaurant dashboard.

    Supported statuses:

    pending
    confirmed
    cancelled
    completed
    """

    def test_func(self):
        return has_dashboard_action(
            self.request.user,
            "reservations",
            "update",
        )

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied

        return super().handle_no_permission()

    def post(self, request, pk):
        reservation = get_object_or_404(
            Reservation,
            pk=pk,
        )

        new_status = request.POST.get("status")

        valid_statuses = {
            choice[0]
            for choice in ReservationStatus.choices
        }

        if new_status not in valid_statuses:
            messages.error(
                request,
                "Invalid reservation status.",
            )

            return redirect("reservations:list")

        old_status = reservation.status

        reservation.status = new_status

        reservation.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        status_labels = dict(
            ReservationStatus.choices
        )

        old_label = status_labels.get(
            old_status,
            old_status,
        )

        new_label = status_labels.get(
            new_status,
            new_status,
        )

        messages.success(
            request,
            f"Reservation for {reservation.full_name} "
            f"changed from {old_label} to {new_label}.",
        )

        return redirect("reservations:list")