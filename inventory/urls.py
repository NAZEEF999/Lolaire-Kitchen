"""
URL configuration for the inventory app.

Registered under app_name="inventory" and included from core/urls.py,
per the project's DJANGO RULES.
"""

from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.IngredientListView.as_view(), name="ingredient_list"),
    path("create/", views.IngredientCreateView.as_view(), name="ingredient_create"),
    path("<int:pk>/", views.IngredientDetailView.as_view(), name="ingredient_detail"),
    path("<int:pk>/edit/", views.IngredientUpdateView.as_view(), name="ingredient_update"),
    path("<int:pk>/delete/", views.IngredientDeleteView.as_view(), name="ingredient_delete"),
    path("<int:pk>/adjust/", views.StockAdjustView.as_view(), name="stock_adjust"),
    path("suppliers/", views.SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/create/", views.SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<int:pk>/edit/", views.SupplierUpdateView.as_view(), name="supplier_update"),
]
