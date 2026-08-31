"""
Enforces the Staff Access system on every request — this is the real
security layer. Sidebar/template {% if %} checks only control what's
*shown*; this middleware controls what's actually *reachable*, so
manually typing a blocked URL is denied the same as clicking a hidden
link would have been.

Runs after AuthenticationMiddleware (request.user must be resolved)
and before views execute. Anonymous requests are passed through
untouched — existing @login_required / LoginRequiredMixin on each view
already handles sending them to the login page; this middleware only
adds the extra module-level gate on top, for authenticated users.
"""

from django.core.exceptions import PermissionDenied

from accounts.permissions import has_admin_panel_access, has_dashboard_access, has_dashboard_section

# Ordered (prefix, module_key) pairs. First match wins, so more specific
# prefixes are listed before the general ones they'd otherwise be
# shadowed by (e.g. "/dashboard/payments/" before "/dashboard/").
# module_key of None means "just require dashboard_enabled, no specific
# section" (the dashboard home page itself, plus stub pages).
DASHBOARD_SECTION_ROUTES = [
    ("/dashboard/payments/", "payments"),
    ("/dashboard/staff/", "staff"),
    ("/dashboard/", None),
    ("/orders/", "orders"),
    ("/reservations/manage/", "reservations"),
    ("/customers/", "customers"),
    ("/tables/", "tables"),
    ("/menu/", "menu"),
    ("/reports/", "reports"),
    ("/inventory/", "inventory"),
]


class StaffAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        if user is not None and user.is_authenticated:
            path = request.path

            if path.startswith("/admin/"):
                if not has_admin_panel_access(user):
                    raise PermissionDenied("You don't have access to the Admin Panel.")
                # Per-model access inside /admin/ is enforced separately
                # by ModulePermissionAdminMixin (see core/admin_mixins.py).

            else:
                for prefix, module_key in DASHBOARD_SECTION_ROUTES:
                    if path.startswith(prefix):
                        if not has_dashboard_access(user):
                            raise PermissionDenied("You don't have access to the Dashboard.")
                        if module_key and not has_dashboard_section(user, module_key):
                            raise PermissionDenied("You don't have access to this section.")
                        break

        return self.get_response(request)
