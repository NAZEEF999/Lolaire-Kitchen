"""
Database query logic for the inventory app.
"""

from django.db.models import Q

from .models import Ingredient, StockAdjustment, Supplier


def get_ingredients(*, search=None, supplier_id=None, low_stock_only=False, include_inactive=False):
    queryset = Ingredient.objects.select_related("supplier")
    if not include_inactive:
        queryset = queryset.active()

    if search:
        queryset = queryset.filter(Q(name__icontains=search))
    if supplier_id:
        queryset = queryset.filter(supplier_id=supplier_id)
    if low_stock_only:
        queryset = queryset.low_stock()

    return queryset


def get_ingredient_by_pk(pk):
    return Ingredient.objects.select_related("supplier").filter(pk=pk).first()


def get_low_stock_ingredients():
    return Ingredient.objects.low_stock().select_related("supplier")


def get_low_stock_count():
    return Ingredient.objects.low_stock().count()


def get_suppliers(*, include_inactive=False):
    queryset = Supplier.objects.all()
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    return queryset


def get_adjustment_history(ingredient):
    return StockAdjustment.objects.filter(ingredient=ingredient).select_related("adjusted_by").order_by("-created_at")
