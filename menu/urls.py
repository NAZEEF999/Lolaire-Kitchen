"""
URL configuration for the menu app.

Registered under app_name="menu" and included from core/urls.py.
"""

from django.urls import path

from . import views

app_name = "menu"

urlpatterns = [
    path("", views.MenuItemListView.as_view(), name="item_list"),
    path("items/create/", views.MenuItemCreateView.as_view(), name="item_create"),
    path("items/<slug:slug>/", views.MenuItemDetailView.as_view(), name="item_detail"),
    path("items/<slug:slug>/edit/", views.MenuItemUpdateView.as_view(), name="item_update"),
    path("items/<slug:slug>/delete/", views.MenuItemDeleteView.as_view(), name="item_delete"),
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/create/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<slug:slug>/", views.CategoryDetailView.as_view(), name="category_detail"),
    path("categories/<slug:slug>/edit/", views.CategoryUpdateView.as_view(), name="category_update"),
    path("categories/<slug:slug>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),
]
