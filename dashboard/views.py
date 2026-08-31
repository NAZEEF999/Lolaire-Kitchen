"""
Views for the dashboard app.

Business logic lives in services.py; views stay lightweight per the
project's rule that views stay lightweight.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts import services as account_services
from accounts.forms import StaffTagForm
from accounts.models import MODULE_ACTIONS, STAFF_ACCESS_MODULES, AccountRecoveryRequest, RecoveryRequestStatus, StaffAccess, StaffTag, User
from accounts.permissions import has_dashboard_action, has_dashboard_section
from orders.models import Order
from reservations.models import Reservation

from . import selectors, services

main_administrator_required = user_passes_test(lambda u: u.is_superuser, login_url="accounts:no_access")
"""
Every Staff Management view (staff_list, staff_access_edit,
staff_tags, staff_security, recovery approve/reject, staff
suspend/reactivate) uses this — deliberately checking is_superuser
directly rather than has_dashboard_section(user, "staff"). Staff
Management is a security-sensitive administrative function, not an
ordinary operational module like Orders or Menu: granting someone the
"staff" StaffAccess module (kept only for backward-compatible JSON
shape) must never let them reach these views. If that module is ever
removed from STAFF_ACCESS_MODULES entirely, nothing here changes,
since it's never consulted for authorization in the first place.
"""


@login_required
def dashboard_home(request):
    """
    Dashboard home page. Statistics, charts, and lists are all
    filtered by the viewer's actual Staff Access module permissions
    (services.filter_stats_by_permission / STAT_MODULE_OWNER) on top
    of the coarser role-based filter — so e.g. a Waiter without
    Payments access sees zero payment figures anywhere on this page,
    not just on the dedicated Payments page. See dashboard.services
    for how each figure/chart/list maps to the module that owns it.

    Every number and chart here comes from a real query — nothing is
    hardcoded or fabricated. Two consequences worth knowing: the Order
    Pipeline below uses Pending/Preparing/Ready/Served — the actual
    orders.models.OrderStatus values — rather than the reference
    design's "New/Confirmed" labels, since those aren't real statuses
    this project's Order model has; and each Live Order's action
    button reads "Start Preparing" rather than "Confirm Order" for the
    same reason — it maps to a real status transition
    (pending → preparing) rather than an invented "confirm" step.
    """
    user = request.user
    stats = services.filter_stats_by_permission(user, services.get_dashboard_statistics())
    can_see_payments = has_dashboard_action(user, "payments", "view")
    can_see_orders = has_dashboard_action(user, "orders", "view")
    can_see_tables = has_dashboard_action(user, "tables", "view")
    can_see_menu = has_dashboard_action(user, "menu", "view")
    can_see_reservations = has_dashboard_action(user, "reservations", "view")
    can_edit_orders = has_dashboard_action(user, "orders", "edit")

    hour = timezone.localtime().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    context = {
        "greeting": greeting,
        "stats": stats,
        "can_see_payments": can_see_payments,
        "can_see_orders": can_see_orders,
        "can_see_tables": can_see_tables,
        "can_edit_orders": can_edit_orders,
        "upcoming_reservations": (
            Reservation.objects.filter(status__in=["pending", "confirmed"]).order_by("reservation_date", "reservation_time")[:6]
            if can_see_reservations
            else []
        ),
        "live_activity": services.get_live_activity(user),
    }

    if can_see_payments:
        revenue_trend = selectors.get_daily_revenue_trend(days=7)
        values = [day["value"] for day in revenue_trend]
        context["revenue_sparkline_points"] = services.sparkline_points(values)
        context["revenue_chart_data"] = {
            # `%-d` (no leading zero) is a Unix-only strftime extension
            # that raises on Windows — building the label manually
            # instead keeps this portable regardless of the host OS.
            "labels": [f"{day['date'].strftime('%b')} {day['date'].day}" for day in revenue_trend],
            "datasets": [{"label": "Revenue", "data": values}],
        }
        if len(values) >= 2 and values[-2]:
            context["revenue_pct_change"] = round(((values[-1] - values[-2]) / values[-2]) * 100, 1)
        else:
            context["revenue_pct_change"] = None

    if can_see_menu:
        popular = services.get_popular_items_chart_data()
        context["popular_items_chart_data"] = popular
        labels = popular.get("labels") or []
        counts = popular["datasets"][0]["data"] if popular.get("datasets") else []
        max_count = max(counts) if counts else 1
        context["best_sellers"] = [
            {"name": name, "count": count, "pct": round((count / max_count) * 100) if max_count else 0}
            for name, count in zip(labels, counts)
        ]
    else:
        context["best_sellers"] = []

    if can_see_orders:
        orders_trend = selectors.get_daily_orders_trend(days=7)
        context["orders_sparkline_points"] = services.sparkline_points([day["value"] for day in orders_trend])

        pipeline_statuses = [("pending", "Pending"), ("preparing", "Preparing"), ("ready", "Ready"), ("served", "Served")]
        pipeline = []
        for status_value, status_label in pipeline_statuses:
            orders_in_status = selectors.get_orders_by_status(status_value)
            pipeline.append({
                "status": status_value,
                "label": status_label,
                "orders": orders_in_status[:5],
                "count": len(orders_in_status),
                "more": max(0, len(orders_in_status) - 5),
            })
        context["order_pipeline"] = pipeline
        context["live_orders"] = selectors.get_orders_by_status("pending")[:5]

    if can_see_tables:
        from tables.models import Table

        context["floor_tables"] = Table.objects.select_related().order_by("table_number")

    needs_attention = []
    if stats.get("cancelled_payments"):
        needs_attention.append({"color": "critical", "text": f"{stats['cancelled_payments']} cancelled payment{'s' if stats['cancelled_payments'] != 1 else ''}", "url": "dashboard:payments_list"})
    if stats.get("pending_orders"):
        needs_attention.append({"color": "warning", "text": f"{stats['pending_orders']} pending order{'s' if stats['pending_orders'] != 1 else ''}", "url": "orders:list"})
    if stats.get("pending_reservations"):
        needs_attention.append({"color": "warning", "text": f"{stats['pending_reservations']} reservation{'s' if stats['pending_reservations'] != 1 else ''} awaiting confirmation", "url": "reservations:list"})
    if stats.get("low_stock_count"):
        needs_attention.append({"color": "critical", "text": f"{stats['low_stock_count']} ingredient{'s' if stats['low_stock_count'] != 1 else ''} low on stock", "url": "inventory:ingredient_list"})
    if can_see_tables and not stats.get("available_tables") and "available_tables" in stats:
        needs_attention.append({"color": "critical", "text": "No tables currently available", "url": "tables:list"})
    if not needs_attention and (can_see_orders or can_see_reservations or can_see_tables):
        needs_attention.append({"color": "success", "text": "Everything looks good — nothing needs attention.", "url": None})
    context["needs_attention"] = needs_attention

    return render(request, "dashboard/home.html", context)


@login_required
def live_updates(request):
    """
    Polled by static/js/dashboard-live.js every ~20s to detect
    brand-new orders without a full page refresh — the "lightweight
    polling" approach the brief asked for instead of adding
    Channels/Redis/Celery for something this project doesn't otherwise
    need. Returns nothing beyond what the viewer's Staff Access
    already permits: requires orders:view specifically (module ON
    alone used to be enough, which meant the View toggle did nothing
    for this endpoint); total_amount is only included if the viewer
    also has payments:view, matching the same payment-leak rule
    applied everywhere else Orders data is shown. `since` is validated
    to a non-negative integer, and the result is always capped
    (get_orders_created_after's own `limit`) regardless of what value
    is supplied — an endpoint must never structurally allow an
    unbounded response.
    """
    since_id = request.GET.get("since", 0)
    try:
        since_id = int(since_id)
    except (TypeError, ValueError):
        since_id = 0
    since_id = max(since_id, 0)

    new_orders = []
    latest_id = 0
    if has_dashboard_action(request.user, "orders", "view"):
        latest_id = selectors.get_latest_order_id()
        can_see_amounts = has_dashboard_action(request.user, "payments", "view")
        if since_id:
            for order in selectors.get_orders_created_after(since_id):
                payload = {
                    "id": order.id,
                    "order_number": order.order_number,
                    "item_count": order.items.count(),
                    "url": reverse("orders:detail", args=[order.pk]),
                }
                if can_see_amounts:
                    payload["total_amount"] = str(order.total_amount)
                new_orders.append(payload)

    return JsonResponse({
        "latest_order_id": latest_id,
        "new_orders": new_orders,
        "pending_recovery_count": (
            AccountRecoveryRequest.objects.filter(status=RecoveryRequestStatus.PENDING).count()
            if request.user.is_superuser
            else None
        ),
    })


@main_administrator_required
def staff_list(request):
    """Staff directory with an at-a-glance summary of each person's access. Super Admin only — see main_administrator_required's docstring for why Staff Management is never gated by the "staff" StaffAccess module."""
    members = User.objects.all().order_by("username").prefetch_related("tags")
    rows = []
    for member in members:
        if member.is_superuser:
            dashboard_enabled = True
            admin_panel_enabled = True
            sections_on_count = len(STAFF_ACCESS_MODULES)
        else:
            access = StaffAccess.objects.filter(user=member).first()
            dashboard_enabled = bool(access and access.dashboard_enabled)
            admin_panel_enabled = bool(access and access.admin_panel_enabled)
            sections_on_count = (
                sum(1 for on in access.dashboard_sections.values() if on) if access else 0
            )
        rows.append({
            "member": member,
            "dashboard_enabled": dashboard_enabled,
            "admin_panel_enabled": admin_panel_enabled,
            "sections_on_count": sections_on_count,
        })
    return render(request, "dashboard/staff_list.html", {"staff": rows, "total_sections": len(STAFF_ACCESS_MODULES)})


@main_administrator_required
def staff_access_edit(request, pk):
    """
    The Staff Access toggle interface — Main Administrator only. A
    superuser's own row can't be reached here (there's nothing to
    toggle: superusers are always fully unrestricted, enforced in
    accounts.permissions regardless of what any StaffAccess row says).
    """
    member = get_object_or_404(User, pk=pk)
    if member.is_superuser:
        messages.info(request, "The Main Administrator always has full access — there's nothing to configure.")
        return redirect("dashboard:staff_list")

    access, _ = StaffAccess.objects.get_or_create(user=member)

    if request.method == "POST":
        dashboard_sections = {key: f"dashboard_section_{key}" in request.POST for key, _label in STAFF_ACCESS_MODULES}
        admin_sections = {key: f"admin_section_{key}" in request.POST for key, _label in STAFF_ACCESS_MODULES}
        dashboard_actions = {
            module: {action: f"dashboard_action_{module}_{action}" in request.POST for action in actions}
            for module, actions in MODULE_ACTIONS.items()
        }
        admin_actions = {
            module: {action: f"admin_action_{module}_{action}" in request.POST for action in actions}
            for module, actions in MODULE_ACTIONS.items()
        }
        account_services.update_staff_access(
            actor=request.user,
            member=member,
            access=access,
            dashboard_enabled="dashboard_enabled" in request.POST,
            admin_panel_enabled="admin_panel_enabled" in request.POST,
            nav_dashboard_to_admin="nav_dashboard_to_admin" in request.POST,
            nav_admin_to_dashboard="nav_admin_to_dashboard" in request.POST,
            dashboard_sections=dashboard_sections,
            admin_sections=admin_sections,
            dashboard_actions=dashboard_actions,
            admin_actions=admin_actions,
        )
        member.tags.set(StaffTag.objects.filter(pk__in=request.POST.getlist("tags")))
        messages.success(request, f"Access updated for {member.get_full_name() or member.username}.")
        return redirect("dashboard:staff_list")

    # Action-level toggles are only shown for modules where they'd say
    # something the module ON/OFF switch doesn't already say — a
    # module whose only defined action is "view" (payments, reports,
    # staff) would just duplicate its own section toggle.
    actionable_modules = {key: actions for key, actions in MODULE_ACTIONS.items() if len(actions) > 1}

    return render(
        request,
        "dashboard/staff_access_edit.html",
        {
            "member": member,
            "access": access,
            "modules": STAFF_ACCESS_MODULES,
            "actionable_modules": actionable_modules,
            "all_tags": StaffTag.objects.all(),
            "member_tag_ids": set(member.tags.values_list("pk", flat=True)),
        },
    )


@main_administrator_required
def staff_tags(request):
    """
    Create/rename/delete organizational tags. Assigning a tag to a
    specific staff member happens on their own Manage Access page
    (staff_access_edit) instead — this page only manages the set of
    tags that exist.
    """
    if request.method == "POST" and request.POST.get("intent") == "create":
        form = StaffTagForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Tag "{form.cleaned_data["name"]}" created.')
        else:
            messages.error(request, form.errors.get("name", ["Couldn't create that tag."])[0])
        return redirect("dashboard:staff_tags")

    return render(request, "dashboard/staff_tags.html", {"tags": StaffTag.objects.all(), "form": StaffTagForm()})


@main_administrator_required
@require_POST
def staff_tag_rename(request, pk):
    tag = get_object_or_404(StaffTag, pk=pk)
    new_name = request.POST.get("name", "").strip()
    if not new_name:
        messages.error(request, "Tag name can't be empty.")
    elif StaffTag.objects.exclude(pk=tag.pk).filter(name__iexact=new_name).exists():
        messages.error(request, f'A tag named "{new_name}" already exists.')
    else:
        tag.name = new_name
        tag.save(update_fields=["name", "updated_at"])
        messages.success(request, "Tag renamed.")
    return redirect("dashboard:staff_tags")


@main_administrator_required
@require_POST
def staff_tag_delete(request, pk):
    tag = get_object_or_404(StaffTag, pk=pk)
    tag.delete()
    messages.success(request, "Tag deleted.")
    return redirect("dashboard:staff_tags")


@login_required
def payments_list(request):
    """
    Payments view, derived entirely from Order.payment_status /
    Order.payment_method — there is no separate Payment model, so this
    reads real order data rather than inventing one. Requires
    payments:view specifically (not just being logged in) — this had
    no permission check at all beyond login before this fix.
    """
    if not has_dashboard_action(request.user, "payments", "view"):
        return redirect("accounts:no_access")
    orders = Order.objects.select_related("customer").order_by("-created_at")
    status = request.GET.get("payment_status")
    if status:
        orders = orders.filter(payment_status=status)
    return render(
        request,
        "dashboard/payments_list.html",
        {"orders": orders[:100], "selected_status": status or ""},
    )


@main_administrator_required
def settings_stub(request):
    """
    Placeholder: no restaurant-settings model exists yet. Super Admin
    only, and honestly marked "not configured yet" in the template
    rather than presenting fake settings — see the brief's explicit
    instruction not to let normal staff think this is functional.
    Inventory had the same "doesn't exist yet" gap and now has a real
    app; Settings would follow the same pattern once actually scoped.
    """
    return render(request, "dashboard/settings_stub.html")


@main_administrator_required
def staff_security(request):
    """
    Main Administrator's review queue: pending account-recovery
    requests, plus a short history of recently-reviewed ones for
    context. See accounts.services for the approval state machine.
    """
    pending = (
        AccountRecoveryRequest.objects.filter(status=RecoveryRequestStatus.PENDING)
        .select_related("user")
        .order_by("created_at")
    )
    recent_reviewed = (
        AccountRecoveryRequest.objects.exclude(status=RecoveryRequestStatus.PENDING)
        .select_related("user", "reviewed_by")
        .order_by("-reviewed_at")[:10]
    )
    return render(
        request,
        "dashboard/staff_security.html",
        {"pending_requests": pending, "recent_reviewed": recent_reviewed},
    )


@main_administrator_required
def audit_log(request):
    """
    Append-only history of security/admin actions — permissions
    changes, staff activation/deactivation, recovery decisions, 2FA
    setup. Main Administrator only. AuditLogEntry.description is
    already restricted at the point every entry is written (see
    accounts.services.record_audit's docstring) to never contain a
    password, TOTP code/secret, reset token, or backup code — this
    view just displays what's there, it doesn't filter anything
    itself, since there's nothing sensitive to filter.
    """
    from accounts.models import AuditLogEntry

    entries = AuditLogEntry.objects.select_related("actor", "target_user").order_by("-created_at")[:200]
    return render(request, "dashboard/audit_log.html", {"entries": entries})


@main_administrator_required
@require_POST
def recovery_approve(request, pk):
    recovery_request = get_object_or_404(AccountRecoveryRequest, pk=pk)
    account_services.approve_recovery(actor=request.user, recovery_request=recovery_request)
    messages.success(request, f"Account recovery approved for {recovery_request.user}. They can now log in.")
    return redirect("dashboard:staff_security")


@main_administrator_required
@require_POST
def recovery_reject(request, pk):
    recovery_request = get_object_or_404(AccountRecoveryRequest, pk=pk)
    reason = request.POST.get("reason", "").strip()
    account_services.reject_recovery(actor=request.user, recovery_request=recovery_request, reason=reason)
    messages.success(request, f"Account recovery request rejected for {recovery_request.user}.")
    return redirect("dashboard:staff_security")


@main_administrator_required
@require_POST
def staff_suspend(request, pk):
    member = get_object_or_404(User, pk=pk)
    try:
        account_services.suspend_account(actor=request.user, member=member)
        messages.success(request, f"{member} has been suspended and can no longer log in.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("dashboard:staff_list")


@main_administrator_required
@require_POST
def staff_reactivate(request, pk):
    member = get_object_or_404(User, pk=pk)
    account_services.reactivate_account(actor=request.user, member=member)
    messages.success(request, f"{member} has been reactivated and can log in again.")
    return redirect("dashboard:staff_list")
