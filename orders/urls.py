"""
URL configuration for the orders app.

Registered under app_name="orders" and included from core/urls.py.
"""

from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("", views.OrderListView.as_view(), name="list"),
    path("create/", views.OrderCreateView.as_view(), name="create"),
    path("<int:pk>/", views.OrderDetailView.as_view(), name="detail"),
    path("<int:pk>/items/add/", views.OrderItemAddView.as_view(), name="item_add"),
    path("<int:pk>/items/<int:item_pk>/remove/", views.OrderItemRemoveView.as_view(), name="item_remove"),
    path("<int:pk>/status/", views.OrderStatusUpdateView.as_view(), name="status_update"),
    path("<int:pk>/payment-status/", views.OrderPaymentStatusUpdateView.as_view(), name="payment_status_update"),
    path("<int:pk>/cancel/", views.OrderCancelView.as_view(), name="cancel"),
    path("<int:pk>/complete/", views.OrderCompleteView.as_view(), name="complete"),
]
