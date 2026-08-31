"""
Views for the inventory app.

Uses Django's generic class-based views, same as menu/orders/tables.
Writes are routed through services.py, not form.save()/self.object
.delete(), per the project's BUSINESS LOGIC rule. Permission gating
uses the newer action-level system (accounts.permissions
.has_dashboard_action) rather than the older role-based mixins seen in
menu/orders — this app is new, so it uses the more precise system that
exists now rather than the pattern that predates it.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from accounts.permissions import has_dashboard_action

from . import selectors, services
from .forms import IngredientForm, IngredientUpdateForm, StockAdjustmentForm, SupplierForm
from .models import Ingredient, Supplier


class InventoryActionRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Gates create/edit/delete/adjust actions beyond the plain "view"
    access the module-level StaffAccess toggle already grants (checked
    by accounts.middleware.StaffAccessMiddleware for every /inventory/
    request) — matches the action-level toggles now configurable from
    Dashboard > Staff > Manage Access.
    """

    inventory_action = "edit"

    def test_func(self):
        return has_dashboard_action(self.request.user, "inventory", self.inventory_action)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


# ── Ingredients ──────────────────────────────────────────────────────────


class IngredientListView(InventoryActionRequiredMixin, ListView):
    inventory_action = "view"
    template_name = "inventory/ingredient_list.html"
    context_object_name = "ingredients"
    paginate_by = 20

    def get_queryset(self):
        return selectors.get_ingredients(
            search=self.request.GET.get("q") or None,
            supplier_id=self.request.GET.get("supplier") or None,
            low_stock_only=self.request.GET.get("low_stock") == "1",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["suppliers"] = selectors.get_suppliers()
        context["low_stock_count"] = selectors.get_low_stock_count()
        context["query"] = self.request.GET.get("q", "")
        context["low_stock_only"] = self.request.GET.get("low_stock") == "1"
        context["can_create"] = has_dashboard_action(self.request.user, "inventory", "create")
        context["can_edit"] = has_dashboard_action(self.request.user, "inventory", "edit")
        context["can_delete"] = has_dashboard_action(self.request.user, "inventory", "delete")
        return context


class IngredientDetailView(InventoryActionRequiredMixin, DetailView):
    inventory_action = "view"
    template_name = "inventory/ingredient_detail.html"
    context_object_name = "ingredient"
    model = Ingredient

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["history"] = selectors.get_adjustment_history(self.object)[:30]
        context["adjust_form"] = StockAdjustmentForm()
        context["can_edit"] = has_dashboard_action(self.request.user, "inventory", "edit")
        context["can_adjust"] = has_dashboard_action(self.request.user, "inventory", "adjust")
        return context


class IngredientCreateView(InventoryActionRequiredMixin, CreateView):
    inventory_action = "create"
    template_name = "inventory/ingredient_form.html"
    form_class = IngredientForm
    success_url = reverse_lazy("inventory:ingredient_list")

    def form_valid(self, form):
        services.create_ingredient(
            name=form.cleaned_data["name"],
            unit=form.cleaned_data["unit"],
            low_stock_threshold=form.cleaned_data["low_stock_threshold"],
            supplier=form.cleaned_data["supplier"],
            opening_quantity=form.cleaned_data.get("opening_quantity") or 0,
            actor=self.request.user,
        )
        messages.success(self.request, "Ingredient added.")
        return redirect(self.success_url)


class IngredientUpdateView(InventoryActionRequiredMixin, UpdateView):
    inventory_action = "edit"
    template_name = "inventory/ingredient_form.html"
    form_class = IngredientUpdateForm
    model = Ingredient
    success_url = reverse_lazy("inventory:ingredient_list")

    def form_valid(self, form):
        services.update_ingredient(
            ingredient=self.object,
            name=form.cleaned_data["name"],
            unit=form.cleaned_data["unit"],
            low_stock_threshold=form.cleaned_data["low_stock_threshold"],
            supplier=form.cleaned_data["supplier"],
            is_active=form.cleaned_data["is_active"],
        )
        messages.success(self.request, "Ingredient updated.")
        return redirect(self.success_url)


class IngredientDeleteView(InventoryActionRequiredMixin, View):
    inventory_action = "delete"

    def post(self, request, pk):
        ingredient = get_object_or_404(Ingredient, pk=pk)
        services.deactivate_ingredient(ingredient=ingredient)
        messages.success(request, f'"{ingredient.name}" removed from active inventory.')
        return redirect("inventory:ingredient_list")


class StockAdjustView(InventoryActionRequiredMixin, View):
    inventory_action = "adjust"

    def post(self, request, pk):
        ingredient = get_object_or_404(Ingredient, pk=pk)
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            try:
                services.record_stock_adjustment(
                    ingredient=ingredient,
                    reason=form.cleaned_data["reason"],
                    quantity_delta=form.signed_quantity(),
                    note=form.cleaned_data["note"],
                    actor=request.user,
                )
                messages.success(request, f"Stock updated for {ingredient.name}.")
            except ValidationError as exc:
                messages.error(request, str(exc.message) if hasattr(exc, "message") else str(exc))
        else:
            messages.error(request, "Couldn't record that stock change — check the quantity entered.")
        return redirect("inventory:ingredient_detail", pk=pk)


# ── Suppliers ────────────────────────────────────────────────────────────


class SupplierListView(InventoryActionRequiredMixin, ListView):
    inventory_action = "view"
    template_name = "inventory/supplier_list.html"
    context_object_name = "suppliers"

    def get_queryset(self):
        return selectors.get_suppliers(include_inactive=True)


class SupplierCreateView(InventoryActionRequiredMixin, CreateView):
    inventory_action = "create"
    template_name = "inventory/supplier_form.html"
    form_class = SupplierForm
    success_url = reverse_lazy("inventory:supplier_list")

    def form_valid(self, form):
        services.create_supplier(**form.cleaned_data)
        messages.success(self.request, "Supplier added.")
        return redirect(self.success_url)


class SupplierUpdateView(InventoryActionRequiredMixin, UpdateView):
    inventory_action = "edit"
    template_name = "inventory/supplier_form.html"
    form_class = SupplierForm
    model = Supplier
    success_url = reverse_lazy("inventory:supplier_list")

    def form_valid(self, form):
        services.update_supplier(supplier=self.object, **form.cleaned_data)
        messages.success(self.request, "Supplier updated.")
        return redirect(self.success_url)
