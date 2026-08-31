"""
Views for the tables app.

Uses Django's generic class-based views. Writes are routed through
services.py (not form.save()/self.object.delete()) so business logic
stays out of views, per the project's BUSINESS LOGIC rule. Pagination
is Django's built-in ListView.paginate_by.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.permissions import has_dashboard_action

from . import selectors, services
from .forms import TableForm, TableStatusForm
from .models import Table, TableStatus


class StaffManagementRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Gates create/edit/delete of tables (structural changes) using the
    Staff Access action-level permissions (Dashboard > Staff > Manage
    Access), replacing what used to be a hardcoded "must be
    Administrator or Manager" check that ignored StaffAccess entirely.
    Each view below sets `tables_action` to the specific action it
    represents, matching MODULE_ACTIONS in accounts/models.py.
    Deliberately doesn't apply to TableStatusUpdateView below — see
    that view's own docstring for why.
    """

    tables_action = "edit"

    def test_func(self):
        return has_dashboard_action(self.request.user, "tables", self.tables_action)

    def handle_no_permission(self):
        # Authenticated staff who simply lack this specific permission
        # should see a clear 403, not get silently bounced to the
        # login page — which would then immediately redirect them
        # right back to the dashboard (StaffLoginView has
        # redirect_authenticated_user=True), with no explanation of
        # what happened.
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class TableListView(StaffManagementRequiredMixin, ListView):
    tables_action = "view"
    template_name = "tables/table_list.html"
    context_object_name = "tables"
    paginate_by = 20

    def get_queryset(self):
        return selectors.get_tables(status=self.request.GET.get("status") or None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_status"] = self.request.GET.get("status", "")
        context["status_choices"] = TableStatus.choices
        context["can_create"] = has_dashboard_action(self.request.user, "tables", "create")
        return context


class TableDetailView(StaffManagementRequiredMixin, DetailView):
    tables_action = "view"
    template_name = "tables/table_detail.html"
    context_object_name = "table"

    def get_queryset(self):
        return Table.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_form"] = TableStatusForm(initial={"status": self.object.status})
        context["can_edit"] = has_dashboard_action(self.request.user, "tables", "edit")
        context["can_delete"] = has_dashboard_action(self.request.user, "tables", "delete")
        return context


class TableCreateView(StaffManagementRequiredMixin, CreateView):
    tables_action = "create"
    form_class = TableForm
    template_name = "tables/table_form.html"
    success_url = reverse_lazy("tables:list")

    def form_valid(self, form):
        self.object = services.create_table(**form.cleaned_data)
        return redirect(self.get_success_url())


class TableUpdateView(StaffManagementRequiredMixin, UpdateView):
    form_class = TableForm
    template_name = "tables/table_form.html"
    success_url = reverse_lazy("tables:list")

    def get_queryset(self):
        return Table.objects.all()

    def form_valid(self, form):
        self.object = services.update_table(table=self.object, **form.cleaned_data)
        return redirect(self.get_success_url())


class TableDeleteView(StaffManagementRequiredMixin, DeleteView):
    tables_action = "delete"
    template_name = "tables/table_confirm_delete.html"
    success_url = reverse_lazy("tables:list")

    def get_queryset(self):
        return Table.objects.all()

    def form_valid(self, form):
        """Soft-delete via services.py — services rejects occupied tables."""
        try:
            services.deactivate_table(table=self.object)
        except ValidationError as exc:
            messages.error(self.request, str(exc.message if hasattr(exc, "message") else exc))
            return redirect(self.object.get_absolute_url())
        return redirect(self.get_success_url())


class TableStatusUpdateView(StaffManagementRequiredMixin, View):
    """
    Marking a table occupied/available/etc. now requires tables:edit —
    previously any logged-in staff member could do this regardless of
    StaffAccess, on the reasoning that it's routine front-of-house
    work distinct from structural edits. That bypassed the action
    permission entirely, so per the hardening pass this now uses the
    same tables:edit gate as structural changes (TableUpdateView).
    """

    tables_action = "edit"

    def post(self, request, pk):
        table = get_object_or_404(Table, pk=pk)
        form = TableStatusForm(request.POST)
        if form.is_valid():
            try:
                services.change_table_status(table=table, new_status=form.cleaned_data["status"])
                messages.success(request, "Table status updated.")
            except ValidationError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Invalid status selected.")
        return redirect(table.get_absolute_url())
