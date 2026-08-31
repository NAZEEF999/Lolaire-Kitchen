"""
URL configuration for the reservations app.
"""

from django.urls import path

from . import views

app_name = "reservations"

urlpatterns = [
    # Public reservation form
    path("", views.ReservationCreateView.as_view(), name="create"),

    # Public success page
    path("thank-you/", views.ReservationSuccessView.as_view(), name="success"),

    # Staff dashboard
    path("manage/", views.ReservationListView.as_view(), name="list"),

    # Staff dashboard status actions
    path(
        "manage/<int:pk>/status/",
        views.ReservationStatusUpdateView.as_view(),
        name="status_update",
    ),
]