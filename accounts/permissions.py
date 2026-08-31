"""
Permission-check helpers for the Staff Access system.

Every gate in the project — the middleware, the Dashboard views, the
Django Admin mixin, the sidebar template context — calls through these
functions rather than reading StaffAccess fields directly. That keeps
the "Main Administrator is always unrestricted" rule enforced in
exactly one place: every function here short-circuits True for a
superuser before it ever looks at the database.

A non-superuser with no StaffAccess row yet (e.g. a brand-new staff
account) is treated as having everything OFF — access is opt-in, only
granted once the Main Administrator explicitly turns something on.
"""

from .models import STAFF_ACCESS_MODULES, StaffAccess

MODULE_KEYS = [key for key, _label in STAFF_ACCESS_MODULES]


def get_staff_access(user):
    """Returns the user's StaffAccess row, or None (never creates one for a superuser)."""
    if not user.is_authenticated or user.is_superuser:
        return None
    try:
        return user.staff_access
    except StaffAccess.DoesNotExist:
        return None


def has_dashboard_access(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    access = get_staff_access(user)
    return bool(access and access.dashboard_enabled)


def has_admin_panel_access(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    access = get_staff_access(user)
    return bool(access and access.admin_panel_enabled)


def can_navigate_dashboard_to_admin(user):
    if user.is_superuser:
        return True
    access = get_staff_access(user)
    return bool(access and access.nav_dashboard_to_admin) and has_admin_panel_access(user)


def can_navigate_admin_to_dashboard(user):
    if user.is_superuser:
        return True
    access = get_staff_access(user)
    return bool(access and access.nav_admin_to_dashboard) and has_dashboard_access(user)


def has_dashboard_section(user, module_key):
    if user.is_superuser:
        return True
    access = get_staff_access(user)
    if not access:
        return False
    return bool(access.dashboard_sections.get(module_key, False))


def has_admin_section(user, module_key):
    if user.is_superuser:
        return True
    access = get_staff_access(user)
    if not access:
        return False
    return bool(access.admin_sections.get(module_key, False))


def has_dashboard_action(user, module_key, action):
    """
    True only if the module itself is ON *and* this specific action is
    ON — action toggles narrow module access, they never widen it, so
    a module that's OFF always wins regardless of what's stored in
    dashboard_actions.
    """
    if user.is_superuser:
        return True
    if not has_dashboard_section(user, module_key):
        return False
    access = get_staff_access(user)
    if not access:
        return False
    return bool(access.dashboard_actions.get(module_key, {}).get(action, False))


def has_admin_action(user, module_key, action):
    if user.is_superuser:
        return True
    if not has_admin_section(user, module_key):
        return False
    access = get_staff_access(user)
    if not access:
        return False
    return bool(access.admin_actions.get(module_key, {}).get(action, False))


def is_main_administrator(user):
    """The one canonical check for 'is this the Super Admin' — used wherever code needs to special-case that account (e.g. preventing self-lockout)."""
    return bool(user.is_authenticated and user.is_superuser)
