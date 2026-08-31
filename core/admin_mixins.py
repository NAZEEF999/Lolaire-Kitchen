"""
Mixins each app's ModelAdmin classes use to enforce Staff Access
permissions inside Django Admin — hiding a model from the index is not
enough on its own (a disabled model's URLs must also be genuinely
unreachable), so these override every permission hook Django Admin
actually checks before rendering a view, not just the one used to
build the index listing.
"""

from accounts.permissions import has_admin_action, has_admin_section


class ModulePermissionAdminMixin:
    """
    Set `lolaire_module = "orders"` (etc, matching accounts.models
    .STAFF_ACCESS_MODULES) on any ModelAdmin using this mixin. A
    superuser always passes. A non-superuser staff member passes only
    if that module is ON *and* the specific action is ON in their
    StaffAccess.admin_actions — view maps to has_view_permission, add
    to has_add_permission, change to has_change_permission, delete to
    has_delete_permission. Each hook is checked independently now:
    Orders ON + Create OFF genuinely blocks add, even though View
    still works. (Previously all four hooks shared one module-only
    check, so any one of them being ON silently allowed all four —
    that was a real bug, now fixed.)
    """

    lolaire_module = None

    def _allowed(self, request, action):
        if not self.lolaire_module:
            return True
        if not has_admin_section(request.user, self.lolaire_module):
            return False
        return has_admin_action(request.user, self.lolaire_module, action)

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_staff and (
            not self.lolaire_module or has_admin_section(request.user, self.lolaire_module)
        )

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff and self._allowed(request, "view")

    def has_add_permission(self, request):
        return request.user.is_active and request.user.is_staff and self._allowed(request, "create")

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff and self._allowed(request, "edit")

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff and self._allowed(request, "delete")


class SuperuserOnlyAdminMixin:
    """
    For ModelAdmin classes that must NEVER be reachable by ordinary
    staff regardless of any StaffAccess toggle — currently UserAdmin
    and StaffAccessAdmin (see accounts/admin.py). Ignores the module
    system entirely on purpose: granting someone "Staff Management"
    access in the Dashboard should never imply they can open the raw
    Django Admin User/StaffAccess screens and edit is_superuser,
    is_staff, groups, or another person's permissions directly.
    """

    def has_module_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_add_permission(self, request):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_active and request.user.is_superuser)
