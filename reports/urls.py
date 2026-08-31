"""
URL configuration for the reports app.

Registered under app_name="reports" and included from core/urls.py.
"sales" and "menu-performance" intentionally map to the same view —
see SalesReportView's docstring.
"""

from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ReportsHomeView.as_view(), name="home"),
    path("revenue/", views.RevenueReportView.as_view(), name="revenue"),
    path("sales/", views.SalesReportView.as_view(), name="sales"),
    path("menu-performance/", views.SalesReportView.as_view(), name="menu_performance"),
    path("orders/", views.OrdersReportView.as_view(), name="orders"),
    path("customers/", views.CustomerReportView.as_view(), name="customers"),
    path("customers/<int:customer_id>/", views.CustomerHistoryReportView.as_view(), name="customer_history"),
    path("tables/", views.TableUtilizationReportView.as_view(), name="tables"),
]
