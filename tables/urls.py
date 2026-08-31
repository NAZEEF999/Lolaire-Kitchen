"""
URL configuration for the tables app.

Registered under app_name="tables" and included from core/urls.py.
"""

from django.urls import path

from . import views

app_name = "tables"

urlpatterns = [
    path("", views.TableListView.as_view(), name="list"),
    path("create/", views.TableCreateView.as_view(), name="create"),
    path("<int:pk>/", views.TableDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.TableUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.TableDeleteView.as_view(), name="delete"),
    path("<int:pk>/status/", views.TableStatusUpdateView.as_view(), name="status_update"),
]
