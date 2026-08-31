"""
URL configuration for the customers app.

Registered under app_name="customers" and included from core/urls.py.
"""

from django.urls import path

from . import views

app_name = "customers"

urlpatterns = [
    path("", views.CustomerListView.as_view(), name="list"),
    path("create/", views.CustomerCreateView.as_view(), name="create"),
    path("<int:pk>/", views.CustomerDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.CustomerUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.CustomerDeleteView.as_view(), name="delete"),
]
