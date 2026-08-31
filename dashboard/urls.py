"""
URL configuration for the dashboard app.

Registered under app_name="dashboard" and included from core/urls.py.
"""

from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("live-updates/", views.live_updates, name="live_updates"),
    path("staff/", views.staff_list, name="staff_list"),
    path("staff/tags/", views.staff_tags, name="staff_tags"),
    path("staff/tags/<int:pk>/rename/", views.staff_tag_rename, name="staff_tag_rename"),
    path("staff/tags/<int:pk>/delete/", views.staff_tag_delete, name="staff_tag_delete"),
    path("staff/<int:pk>/access/", views.staff_access_edit, name="staff_access_edit"),
    path("staff/<int:pk>/suspend/", views.staff_suspend, name="staff_suspend"),
    path("staff/<int:pk>/reactivate/", views.staff_reactivate, name="staff_reactivate"),
    path("staff/security/", views.staff_security, name="staff_security"),
    path("staff/audit-log/", views.audit_log, name="audit_log"),
    path("staff/security/<int:pk>/approve/", views.recovery_approve, name="recovery_approve"),
    path("staff/security/<int:pk>/reject/", views.recovery_reject, name="recovery_reject"),
    path("payments/", views.payments_list, name="payments_list"),
    path("settings/", views.settings_stub, name="settings"),
]
