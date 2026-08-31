"""
Views for the menu app.

Uses Django's generic class-based views rather than hand-rolled
list/detail/create/update/delete logic. Writes are routed through
services.py (not form.save()/self.object.delete()) so business logic
stays out of views, per the project's BUSINESS LOGIC rule. Pagination
is Django's built-in ListView.paginate_by rather than a custom
implementation.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.permissions import has_dashboard_action

from . import selectors, services
from .forms import CategoryForm, MenuItemForm
from .models import Category, MenuItem


class StaffManagementRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Gates create/edit/delete of menu content using the Staff Access
    action-level permissions (Dashboard > Staff > Manage Access),
    replacing what used to be a hardcoded "must be Administrator or
    Manager" check that ignored StaffAccess entirely — a Cashier
    explicitly granted Menu edit access still couldn't get in before
    this fix. Each view below sets `menu_action` to the specific
    action it represents (create/edit/delete), matching MODULE_ACTIONS
    in accounts/models.py.
    """

    menu_action = "edit"

    def test_func(self):
        return has_dashboard_action(self.request.user, "menu", self.menu_action)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


# ── Menu items ──────────────────────────────────────────────────────────


class MenuItemListView(StaffManagementRequiredMixin, ListView):
    """Browsable, searchable, filterable, paginated menu item list."""

    menu_action = "view"
    template_name = "menu/item_list.html"
    context_object_name = "menu_items"
    paginate_by = 12

    def get_queryset(self):
        return selectors.get_menu_items(
            category_slug=self.request.GET.get("category") or None,
            is_available=self._parse_bool(self.request.GET.get("is_available")),
            search=self.request.GET.get("q") or None,
        )

    @staticmethod
    def _parse_bool(value):
        if value in ("true", "1"):
            return True
        if value in ("false", "0"):
            return False
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = selectors.get_active_categories()
        context["query"] = self.request.GET.get("q", "")
        context["selected_category"] = self.request.GET.get("category", "")
        context["selected_availability"] = self.request.GET.get("is_available", "")
        context["can_create"] = has_dashboard_action(self.request.user, "menu", "create")
        return context


class MenuItemDetailView(StaffManagementRequiredMixin, DetailView):
    menu_action = "view"
    template_name = "menu/item_detail.html"
    context_object_name = "menu_item"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return MenuItem.objects.select_related("category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = has_dashboard_action(self.request.user, "menu", "edit")
        context["can_delete"] = has_dashboard_action(self.request.user, "menu", "delete")
        return context


class MenuItemCreateView(StaffManagementRequiredMixin, CreateView):
    menu_action = "create"
    form_class = MenuItemForm
    template_name = "menu/item_form.html"
    success_url = reverse_lazy("menu:item_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Template renders an inline "quick add category" modal alongside
        # the main form (submitted separately, via menu:category_create) —
        # display-only context, not part of this view's own form_valid.
        context["category_form"] = CategoryForm()
        return context

    def form_valid(self, form):
        self.object = services.create_menu_item(**form.cleaned_data)
        return redirect(self.get_success_url())


class MenuItemUpdateView(StaffManagementRequiredMixin, UpdateView):
    form_class = MenuItemForm
    template_name = "menu/item_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("menu:item_list")

    def get_queryset(self):
        return MenuItem.objects.select_related("category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category_form"] = CategoryForm()
        return context

    def form_valid(self, form):
        self.object = services.update_menu_item(menu_item=self.object, **form.cleaned_data)
        return redirect(self.get_success_url())


class MenuItemDeleteView(StaffManagementRequiredMixin, DeleteView):
    menu_action = "delete"
    template_name = "menu/item_confirm_delete.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("menu:item_list")

    def get_queryset(self):
        return MenuItem.objects.select_related("category")

    def form_valid(self, form):
        """Soft-delete via services.py instead of a real DB delete."""
        services.deactivate_menu_item(menu_item=self.object)
        return redirect(self.get_success_url())


# ── Categories ──────────────────────────────────────────────────────────


class CategoryListView(StaffManagementRequiredMixin, ListView):
    menu_action = "view"
    template_name = "menu/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return selectors.get_active_categories()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = has_dashboard_action(self.request.user, "menu", "create")
        return context


class CategoryDetailView(StaffManagementRequiredMixin, DetailView):
    menu_action = "view"
    template_name = "menu/category_detail.html"
    context_object_name = "category"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Category.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["menu_items"] = selectors.get_menu_items(category_slug=self.object.slug)
        context["can_edit"] = has_dashboard_action(self.request.user, "menu", "edit")
        context["can_delete"] = has_dashboard_action(self.request.user, "menu", "delete")
        return context


class CategoryCreateView(StaffManagementRequiredMixin, CreateView):
    menu_action = "create"
    form_class = CategoryForm
    template_name = "menu/category_form.html"
    success_url = reverse_lazy("menu:category_list")

    def _is_ajax(self):
        # Used by the "quick add category" modal on the menu item form,
        # which posts here via fetch() instead of a full-page submit, so
        # the staff member doesn't lose an in-progress item form. The
        # standalone Categories page still gets a normal redirect.
        return self.request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def form_valid(self, form):
        self.object = services.create_category(**form.cleaned_data)

        if self._is_ajax():
            return JsonResponse({"id": self.object.id, "name": self.object.name})

        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if self._is_ajax():
            # form.errors itself holds ValidationError objects, which
            # JsonResponse's encoder can't serialize — get_json_data()
            # is Django's built-in conversion to plain, JSON-safe dicts.
            return JsonResponse({"errors": form.errors.get_json_data()}, status=400)

        return super().form_invalid(form)


class CategoryUpdateView(StaffManagementRequiredMixin, UpdateView):
    form_class = CategoryForm
    template_name = "menu/category_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("menu:category_list")

    def get_queryset(self):
        return Category.objects.all()

    def form_valid(self, form):
        self.object = services.update_category(category=self.object, **form.cleaned_data)
        return redirect(self.get_success_url())


class CategoryDeleteView(StaffManagementRequiredMixin, DeleteView):
    menu_action = "delete"
    template_name = "menu/category_confirm_delete.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("menu:category_list")

    def get_queryset(self):
        return Category.objects.all()

    def form_valid(self, form):
        """Soft-delete (cascading to its items) via services.py instead of a real DB delete."""
        services.deactivate_category(category=self.object)
        return redirect(self.get_success_url())
