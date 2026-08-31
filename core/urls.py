"""
Root URL configuration for the Restaurant Management System.

Every application is included here under its own path prefix, per the
project's DJANGO RULES (each app owns its own urls.py + app_name, and
the main urls.py must include every application).

The public website is served by the `storefront` app at the project
root. `reservations` is also public-facing (no login required) but is
mounted under its own "reservations/" prefix, per that app's own
urls.py (public create at "reservations/", staff management at
"reservations/manage/").
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("storefront.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("menu/", include("menu.urls")),
    path("orders/", include("orders.urls")),
    path("customers/", include("customers.urls")),
    path("tables/", include("tables.urls")),
    path("reports/", include("reports.urls")),
    path("inventory/", include("inventory.urls")),
    path("reservations/", include("reservations.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.BASE_DIR / "media")
