"""
Models for the accounts app.

Defines the system's custom User model and its four staff roles.
Setting AUTH_USER_MODEL to "accounts.User" is the one necessary
addition to core/settings.py this phase requires — see the settings
file for the change.
"""

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models

from core.models import TimeStampedModel

from .validators import phone_number_validator


class UserRole(models.TextChoices):
    ADMINISTRATOR = "administrator", "Administrator"
    MANAGER = "manager", "Manager"
    CASHIER = "cashier", "Cashier"
    WAITER = "waiter", "Waiter"


class AccountStatus(models.TextChoices):
    """
    Drives whether a User can actually log in — see the `is_active`
    note on the field below. Only accounts.services should ever change
    this (via the account-status transition helpers there); nowhere
    else writes to it directly.
    """

    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    RECOVERY_PENDING = "recovery_pending", "Recovery Pending"
    RECOVERY_REJECTED = "recovery_rejected", "Recovery Rejected"


class StaffTag(TimeStampedModel):
    """
    A purely organizational label the Main Administrator can attach to
    staff — "Manager", "Kitchen", "Supervisor" and so on — for
    identification only. Deliberately NOT read anywhere in
    accounts.permissions or any other access-control code: a tag never
    grants, implies, or widens a permission. What a staff member can
    actually see and do is entirely decided by their StaffAccess row.
    A staff member can hold any number of tags (or none).
    """

    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Staff Tag"
        verbose_name_plural = "Staff Tags"
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserManager(DjangoUserManager):
    """
    Same behaviour as Django's default UserManager, except
    createsuperuser always gets the Administrator role so `is_staff`,
    `is_superuser`, and `role` stay consistent with each other.
    """

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.ADMINISTRATOR)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser, TimeStampedModel):
    """
    Custom user model for restaurant staff.

    Extends Django's AbstractUser — keeping username-based login, which
    suits till/counter staff who may not have an email address — and
    adds the `role` field used throughout the system for permissions
    and UI. Also inherits TimeStampedModel per the project's MODELS
    rule, so every account tracks created_at/updated_at alongside
    AbstractUser's own date_joined/last_login.
    """

    objects = UserManager()

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.WAITER,
        help_text="Determines what this staff member can access in the system.",
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[phone_number_validator],
        help_text="Optional contact number, e.g. 08012345678.",
    )

    # ── Account recovery state ──────────────────────────────────────
    # `account_status` is the human-readable record of *why* an account
    # can or can't log in. `is_active` (from AbstractUser) is what
    # Django's own ModelBackend actually checks on every login attempt
    # — so the two are always kept in lockstep by the transition
    # helpers in accounts.services, rather than introducing a second,
    # parallel login gate.
    account_status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        help_text="Set only via accounts.services — see AccountStatus.",
    )

    # ── Main Administrator 2FA (TOTP) ───────────────────────────────
    # Only ever set for the superuser account, via the Dashboard's
    # Staff Security > Set Up 2FA page. Storing the shared secret
    # itself (rather than a hash of it) is a deliberate, necessary
    # exception to "never store secrets": TOTP verification requires
    # recomputing the current code server-side from this same secret,
    # the same way an authenticator app does — unlike a password or a
    # backup code, it isn't something a hash can be checked against.
    totp_secret = models.CharField(
        max_length=32, blank=True, help_text="Base32 TOTP secret. Blank until 2FA is set up."
    )
    totp_enabled = models.BooleanField(default=False)

    # Organizational-only labels — see StaffTag's docstring. Deliberately
    # separate from `role` above: `role` still drives is_staff and
    # dashboard stat scoping (pre-existing, unchanged), while `tags` is
    # purely descriptive and never consulted for any access decision.
    tags = models.ManyToManyField(StaffTag, blank=True, related_name="staff_members")

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["username"]

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_administrator(self):
        return self.role == UserRole.ADMINISTRATOR

    @property
    def is_manager(self):
        return self.role == UserRole.MANAGER

    @property
    def is_cashier(self):
        return self.role == UserRole.CASHIER

    @property
    def is_waiter(self):
        return self.role == UserRole.WAITER


# The fixed set of modules the Main Administrator can toggle per staff
# member, for both the custom Dashboard and Django Admin. Kept as one
# shared list (rather than two separately-maintained lists) so adding a
# future module — e.g. "inventory" — only ever means adding one entry
# here.
STAFF_ACCESS_MODULES = [
    ("orders", "Orders"),
    ("reservations", "Reservations"),
    ("customers", "Customers"),
    ("tables", "Tables"),
    ("menu", "Menu"),
    ("payments", "Payments"),
    ("reports", "Reports"),
    ("inventory", "Inventory"),
    ("staff", "Staff Management"),
]


def _default_sections():
    """New staff start with every section OFF — access is opt-in, granted by the Main Administrator."""
    return {key: False for key, _label in STAFF_ACCESS_MODULES}


# Which action-level toggles make sense for each module — grounded in
# the create/edit/delete/etc. views that already exist for that app
# (see e.g. menu/urls.py, orders/urls.py), so nothing here is a
# permission for a capability that doesn't actually exist yet. A
# module left out of this dict (there are none currently) would simply
# fall back to its single ON/OFF from STAFF_ACCESS_MODULES — action
# toggles narrow that gate further, they never widen it.
MODULE_ACTIONS = {
    "orders": ["view", "create", "edit", "cancel", "complete"],
    "reservations": ["view", "manage"],  # manage = confirm/cancel/complete an incoming request
    "menu": ["view", "create", "edit", "delete"],
    "customers": ["view", "create", "edit", "delete"],
    "tables": ["view", "create", "edit", "delete"],
    "payments": ["view", "edit"],  # "edit" = marking Paid/Refunded/etc (orders.OrderPaymentStatusUpdateView) — no other payment CRUD exists
    "reports": ["view"],
    "inventory": ["view", "create", "edit", "delete", "adjust"],  # "adjust" = record a stock change, distinct from editing an ingredient's own fields (threshold, supplier, etc.)
    "staff": ["view"],  # editing another staff member's access is Main-Administrator-only, enforced in code, not a toggle
}


def _default_actions():
    """New staff start with every action OFF, same opt-in rule as _default_sections."""
    return {module: {action: False for action in actions} for module, actions in MODULE_ACTIONS.items()}


class StaffAccess(TimeStampedModel):
    """
    The simple ON/OFF permission configuration for one staff member,
    covering the custom Dashboard, Django Admin, and navigation between
    the two. One row per non-superuser User; superusers (the Main
    Administrator) never need a row — see accounts.permissions, which
    always grants a superuser full access regardless of what's stored
    here.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_access")

    dashboard_enabled = models.BooleanField(default=False, help_text="Can this staff member open the custom Dashboard at all?")
    admin_panel_enabled = models.BooleanField(default=False, help_text="Can this staff member open Django Admin at /admin/ at all?")

    nav_dashboard_to_admin = models.BooleanField(
        default=False, help_text="Show the 'Admin Panel' button inside the Dashboard."
    )
    nav_admin_to_dashboard = models.BooleanField(
        default=False, help_text="Show the 'Back to Dashboard' link inside Django Admin."
    )

    dashboard_sections = models.JSONField(default=_default_sections, help_text="Per-module ON/OFF for the Dashboard sidebar.")
    admin_sections = models.JSONField(default=_default_sections, help_text="Per-module ON/OFF for Django Admin.")

    dashboard_actions = models.JSONField(
        default=_default_actions,
        help_text="Per-module action-level ON/OFF for the Dashboard (view/create/edit/delete, only where meaningful — see MODULE_ACTIONS). Only takes effect where the matching dashboard_sections entry is also ON.",
    )
    admin_actions = models.JSONField(
        default=_default_actions,
        help_text="Per-module action-level ON/OFF for Django Admin. Only takes effect where the matching admin_sections entry is also ON.",
    )

    class Meta:
        verbose_name = "Staff Access"
        verbose_name_plural = "Staff Access"

    def __str__(self):
        return f"Access settings for {self.user}"


class RecoveryRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class AccountRecoveryRequest(TimeStampedModel):
    """
    One row per password-recovery attempt that reached the "new
    password set" step. Created the moment a staff member completes
    StaffPasswordResetConfirmView; from that point the account's
    `account_status` is RECOVERY_PENDING and login stays blocked
    (is_active=False) until the Main Administrator reviews this row
    from Dashboard > Staff Security.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recovery_requests")
    status = models.CharField(max_length=20, choices=RecoveryRequestStatus.choices, default=RecoveryRequestStatus.PENDING)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_recovery_requests"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Account Recovery Request"
        verbose_name_plural = "Account Recovery Requests"

    def __str__(self):
        return f"Recovery request for {self.user} ({self.get_status_display()})"


class BackupCode(TimeStampedModel):
    """
    One-time 2FA backup codes for the Main Administrator, generated
    once when TOTP is first set up — so a lost/wiped authenticator
    device doesn't lock the Super Admin out permanently. Stored hashed
    via Django's own password hasher (see accounts.services), exactly
    like a password: never recoverable once shown to the user, only
    checkable against what they type back in later.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="backup_codes")
    code_hash = models.CharField(max_length=128)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Backup Code"
        verbose_name_plural = "Backup Codes"

    def __str__(self):
        return f"Backup code for {self.user} ({'used' if self.used_at else 'unused'})"


class AuditAction(models.TextChoices):
    PERMISSIONS_CHANGED = "permissions_changed", "Permissions changed"
    STAFF_ACTIVATED = "staff_activated", "Staff activated"
    STAFF_DEACTIVATED = "staff_deactivated", "Staff deactivated"
    RECOVERY_REQUESTED = "recovery_requested", "Recovery requested"
    RECOVERY_APPROVED = "recovery_approved", "Recovery approved"
    RECOVERY_REJECTED = "recovery_rejected", "Recovery rejected"
    RECOVERY_BLOCKED = "recovery_blocked", "Recovery blocked (account suspended)"
    TOTP_ENABLED = "totp_enabled", "Two-factor authentication enabled"


class AuditLogEntry(TimeStampedModel):
    """
    Who did what to whom, for the Staff Security screen. Append-only —
    no view anywhere in the project updates or deletes a row.
    `description` must only ever hold the kind of plain-language
    summary a Main Administrator should be able to read back later
    (e.g. "Payments: ON → OFF"); never a password, TOTP code/secret,
    reset token, or backup code.
    """

    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_actions_performed")
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_actions_received")
    action = models.CharField(max_length=30, choices=AuditAction.choices)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log Entries"

    def __str__(self):
        return f"{self.get_action_display()} — {self.target_user or 'system'}"
