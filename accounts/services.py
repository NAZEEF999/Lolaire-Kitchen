"""
Business logic for the accounts app.

Views call into this module for anything that writes to the database
or orchestrates multiple steps, keeping views.py lightweight per the
project's BUSINESS LOGIC rule.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import AccountRecoveryRequest, AccountStatus, AuditAction, AuditLogEntry, RecoveryRequestStatus
from .validators import validate_role_change_allowed

User = get_user_model()


@transaction.atomic
def create_staff_user(
    *, username, password, role, first_name="", last_name="", email="", phone_number=""
):
    """Create a new staff account through a single, consistent code path."""
    return User.objects.create_user(
        username=username,
        password=password,
        role=role,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone_number=phone_number,
    )


def update_profile(*, user, first_name=None, last_name=None, email=None, phone_number=None):
    """
    Update a user's own profile fields. Only the fields explicitly
    passed (not None) are changed and saved.
    """
    fields_to_update = []

    if first_name is not None:
        user.first_name = first_name
        fields_to_update.append("first_name")
    if last_name is not None:
        user.last_name = last_name
        fields_to_update.append("last_name")
    if email is not None:
        user.email = email
        fields_to_update.append("email")
    if phone_number is not None:
        user.phone_number = phone_number
        fields_to_update.append("phone_number")

    if fields_to_update:
        fields_to_update.append("updated_at")
        user.save(update_fields=fields_to_update)

    return user


@transaction.atomic
def change_user_role(*, user, new_role):
    """
    Change a user's role. Enforces (via validators.validate_role_change_allowed)
    that the last remaining Administrator can never be demoted, which
    would lock everyone out of the highest privilege level.
    """
    validate_role_change_allowed(user, new_role)
    user.role = new_role
    # "is_staff" is included even though this function only sets
    # "role" directly: the pre_save signal (sync_staff_status_with_role)
    # mutates instance.is_staff based on the new role, and update_fields
    # restricts the SQL UPDATE to exactly this list — without "is_staff"
    # here, the signal's change would be silently discarded.
    user.save(update_fields=["role", "is_staff", "updated_at"])
    return user


def record_audit(*, actor, action, target_user=None, description=""):
    """
    The single write path for every AuditLogEntry — see that model's
    docstring for what may (a plain-language summary) and may never
    (a password, TOTP code/secret, reset token, or backup code) go in
    `description`.
    """
    return AuditLogEntry.objects.create(actor=actor, target_user=target_user, action=action, description=description)


@transaction.atomic
def complete_password_reset(*, user):
    """
    Called immediately after a staff member successfully sets a new
    password through StaffPasswordResetConfirmView. Setting the
    password alone must never restore login access — this is what
    enforces that.

    Two cases:

    - Normal case (account_status was ACTIVE or RECOVERY_REJECTED —
      i.e. this genuinely was just a forgotten password): the account
      moves to RECOVERY_PENDING, is_active is turned off, and a new
      AccountRecoveryRequest is opened for the Main Administrator to
      review from Dashboard > Staff Security.
    - Suspended case: a password reset must NOT undo a Main
      Administrator's deliberate suspension decision, so account_status
      is left exactly as SUSPENDED and no AccountRecoveryRequest is
      created — there is nothing here for the Administrator to
      "approve into"; un-suspending is its own explicit action.

    If a PENDING request already exists for this user (e.g. they used
    the reset link more than once before the Main Administrator
    reviewed the first one), that same row is reused rather than
    creating a second one — one active pending request per account at
    a time, so the Staff Security queue can't fill up with duplicates
    for a single person. Older completed/rejected requests are left
    alone as history.

    NOTE (superuser accounts): deliberately does nothing at all for a
    superuser for now. The Main Administrator's recovery is meant to
    go through a separate TOTP-verified flow rather than this
    approval-queue one (a single Main Administrator approving their
    own recovery request would be meaningless, and there's no one else
    to approve it) — see accounts/totp.py. That flow isn't wired up to
    the "Forgot Password" entry point yet, so until it is, a superuser
    using this standard reset form keeps today's existing behaviour
    (password changes immediately, no pending state).
    """
    if user.is_superuser:
        return None

    if user.account_status == AccountStatus.SUSPENDED:
        record_audit(
            actor=None,
            action=AuditAction.RECOVERY_BLOCKED,
            target_user=user,
            description="Password reset completed while account was suspended — suspension unchanged, no recovery request opened.",
        )
        return None

    user.account_status = AccountStatus.RECOVERY_PENDING
    user.is_active = False
    user.save(update_fields=["account_status", "is_active", "updated_at"])

    existing_pending = AccountRecoveryRequest.objects.filter(user=user, status=RecoveryRequestStatus.PENDING).first()
    if existing_pending:
        record_audit(
            actor=None,
            action=AuditAction.RECOVERY_REQUESTED,
            target_user=user,
            description="Password reset repeated while a recovery request was already pending — reused the existing request rather than opening a duplicate.",
        )
        return existing_pending

    request = AccountRecoveryRequest.objects.create(user=user, status=RecoveryRequestStatus.PENDING)
    record_audit(
        actor=None,
        action=AuditAction.RECOVERY_REQUESTED,
        target_user=user,
        description="Password reset completed — awaiting Main Administrator approval before login is restored.",
    )
    return request


@transaction.atomic
def approve_recovery(*, actor, recovery_request):
    """
    Restores login access for the staff member behind `recovery_request`.
    Only ever called from a Main-Administrator-only view (see
    dashboard.views.recovery_approve) — enforced there, not re-checked
    here, matching the pattern the rest of this module already follows
    (e.g. change_user_role trusts its caller for the same reason).
    Silently does nothing if the request was already reviewed, so a
    double form submission can't double-process it.
    """
    if recovery_request.status != RecoveryRequestStatus.PENDING:
        return recovery_request

    recovery_request.status = RecoveryRequestStatus.APPROVED
    recovery_request.reviewed_by = actor
    recovery_request.reviewed_at = timezone.now()
    recovery_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

    member = recovery_request.user
    member.account_status = AccountStatus.ACTIVE
    member.is_active = True
    member.save(update_fields=["account_status", "is_active", "updated_at"])

    record_audit(
        actor=actor,
        action=AuditAction.RECOVERY_APPROVED,
        target_user=member,
        description="Account recovery approved — login access restored.",
    )
    return recovery_request


@transaction.atomic
def reject_recovery(*, actor, recovery_request, reason=""):
    """
    Leaves the staff member's account unable to log in. See
    approve_recovery's docstring for the authorization note.
    """
    if recovery_request.status != RecoveryRequestStatus.PENDING:
        return recovery_request

    recovery_request.status = RecoveryRequestStatus.REJECTED
    recovery_request.reviewed_by = actor
    recovery_request.reviewed_at = timezone.now()
    recovery_request.rejection_reason = reason
    recovery_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"])

    member = recovery_request.user
    member.account_status = AccountStatus.RECOVERY_REJECTED
    # is_active stays False — rejection keeps the account locked, it doesn't additionally punish it.
    member.save(update_fields=["account_status", "updated_at"])

    record_audit(
        actor=actor,
        action=AuditAction.RECOVERY_REJECTED,
        target_user=member,
        description=f"Account recovery request rejected.{f' Reason: {reason}' if reason else ''}",
    )
    return recovery_request


@transaction.atomic
def suspend_account(*, actor, member):
    """
    Immediately blocks login for a staff account — e.g. a compromised
    account. Refuses to suspend a superuser at all (there's exactly
    one Main Administrator; suspending it has no recovery path) and
    refuses self-suspension for anyone, closing off the "Super Admin
    accidentally locks themselves out" failure mode at the one place
    every suspend action passes through.
    """
    if member.is_superuser:
        raise ValueError("The Main Administrator's account can't be suspended.")
    if actor is not None and actor.pk == member.pk:
        raise ValueError("You can't suspend your own account.")

    member.account_status = AccountStatus.SUSPENDED
    member.is_active = False
    member.save(update_fields=["account_status", "is_active", "updated_at"])

    record_audit(actor=actor, action=AuditAction.STAFF_DEACTIVATED, target_user=member, description="Account suspended.")
    return member


@transaction.atomic
def reactivate_account(*, actor, member):
    """The explicit, deliberate counterpart to suspend_account — the only other way a SUSPENDED account regains login access, per complete_password_reset's docstring."""
    member.account_status = AccountStatus.ACTIVE
    member.is_active = True
    member.save(update_fields=["account_status", "is_active", "updated_at"])

    record_audit(actor=actor, action=AuditAction.STAFF_ACTIVATED, target_user=member, description="Account reactivated.")
    return member


def _generate_and_store_backup_codes(user, *, count=10):
    """
    Wipes any existing (unused or used) backup codes and issues a
    fresh set — used both by initial TOTP setup and by an explicit
    "regenerate backup codes" action. Returns the plaintext codes for
    one-time display; only the hash is ever persisted.
    """
    from django.contrib.auth.hashers import make_password

    from .models import BackupCode
    from .totp import generate_backup_codes

    BackupCode.objects.filter(user=user).delete()
    codes = generate_backup_codes(count)
    BackupCode.objects.bulk_create([BackupCode(user=user, code_hash=make_password(code)) for code in codes])
    return codes


def regenerate_backup_codes(user):
    """Public entry point for 'I've used most of my backup codes, give me a fresh set' — see _generate_and_store_backup_codes."""
    return _generate_and_store_backup_codes(user)


def _diff_bool_dict(old, new, labels, prefix=""):
    lines = []
    for key in new:
        old_val, new_val = bool(old.get(key, False)), bool(new.get(key, False))
        if old_val != new_val:
            lines.append(f"{prefix}{labels.get(key, key)}: {'ON' if old_val else 'OFF'} → {'ON' if new_val else 'OFF'}")
    return lines


def _diff_action_dict(old, new, labels, prefix=""):
    lines = []
    for module, actions in new.items():
        module_label = labels.get(module, module)
        for action, new_val in actions.items():
            old_val, new_val = bool(old.get(module, {}).get(action, False)), bool(new_val)
            if old_val != new_val:
                lines.append(f"{prefix}{module_label} — {action}: {'ON' if old_val else 'OFF'} → {'ON' if new_val else 'OFF'}")
    return lines


@transaction.atomic
def update_staff_access(
    *,
    actor,
    member,
    access,
    dashboard_enabled,
    admin_panel_enabled,
    nav_dashboard_to_admin,
    nav_admin_to_dashboard,
    dashboard_sections,
    admin_sections,
    dashboard_actions,
    admin_actions,
):
    """
    Applies a full StaffAccess update in one save, and records exactly
    what changed as one audit entry (e.g. "Payments: ON → OFF") — a
    save where nothing actually changed produces no audit line, so
    re-submitting the form unchanged doesn't create log noise.
    """
    from .models import STAFF_ACCESS_MODULES

    labels = dict(STAFF_ACCESS_MODULES)
    changes = []
    if access.dashboard_enabled != dashboard_enabled:
        changes.append(f"Dashboard access: {'ON' if access.dashboard_enabled else 'OFF'} → {'ON' if dashboard_enabled else 'OFF'}")
    if access.admin_panel_enabled != admin_panel_enabled:
        changes.append(f"Admin Panel access: {'ON' if access.admin_panel_enabled else 'OFF'} → {'ON' if admin_panel_enabled else 'OFF'}")
    changes += _diff_bool_dict(access.dashboard_sections, dashboard_sections, labels, prefix="Dashboard – ")
    changes += _diff_bool_dict(access.admin_sections, admin_sections, labels, prefix="Admin – ")
    changes += _diff_action_dict(access.dashboard_actions, dashboard_actions, labels, prefix="Dashboard ")
    changes += _diff_action_dict(access.admin_actions, admin_actions, labels, prefix="Admin ")

    access.dashboard_enabled = dashboard_enabled
    access.admin_panel_enabled = admin_panel_enabled
    access.nav_dashboard_to_admin = nav_dashboard_to_admin
    access.nav_admin_to_dashboard = nav_admin_to_dashboard
    access.dashboard_sections = dashboard_sections
    access.admin_sections = admin_sections
    access.dashboard_actions = dashboard_actions
    access.admin_actions = admin_actions
    access.save()

    if changes:
        record_audit(actor=actor, action=AuditAction.PERMISSIONS_CHANGED, target_user=member, description="\n".join(changes))
    return access


def begin_totp_setup(user):
    """
    Step 1 of enabling 2FA: generates and saves a fresh secret
    (totp_enabled stays False until confirm_totp_setup verifies the
    user actually has it working — no point enabling 2FA on a secret
    nobody has successfully scanned yet). Safe to call again before
    confirming; each call replaces the pending secret.
    """
    from .totp import generate_totp_secret

    user.totp_secret = generate_totp_secret()
    user.totp_enabled = False
    user.save(update_fields=["totp_secret", "totp_enabled", "updated_at"])
    return user.totp_secret


@transaction.atomic
def confirm_totp_setup(*, user, code):
    """
    Step 2: proves the user's authenticator app actually has the
    secret from begin_totp_setup by checking one live code from it,
    then turns 2FA on and issues backup codes (shown to the user
    exactly once by the view that calls this — nothing here or after
    this function keeps the plaintext).
    """
    from .totp import verify_totp

    if not user.totp_secret or not verify_totp(user.totp_secret, code):
        return None

    user.totp_enabled = True
    user.save(update_fields=["totp_enabled", "updated_at"])
    record_audit(actor=user, action=AuditAction.TOTP_ENABLED, target_user=user, description="Two-factor authentication enabled.")
    return _generate_and_store_backup_codes(user)


def verify_totp_or_backup_code(*, user, code):
    """
    Used by the Main Administrator recovery flow (see
    accounts.views.AdminRecoveryVerifyView): true if `code` is either
    a currently-valid TOTP code, or an unused backup code — in which
    case that backup code is immediately marked used and can't be
    reused. Checks TOTP first since that's the expected common case.
    """
    from django.contrib.auth.hashers import check_password
    from django.utils import timezone

    from .models import BackupCode
    from .totp import verify_totp

    if not user.totp_enabled or not user.totp_secret:
        return False

    if verify_totp(user.totp_secret, code):
        return True

    for backup_code in BackupCode.objects.filter(user=user, used_at__isnull=True):
        if check_password(code, backup_code.code_hash):
            backup_code.used_at = timezone.now()
            backup_code.save(update_fields=["used_at", "updated_at"])
            return True

    return False


# ── TOTP brute-force protection ─────────────────────────────────────────
# A 6-digit code has only 1,000,000 possibilities, so unlimited attempts
# are unacceptable — but the account must never be locked permanently
# (that would itself be a denial-of-service against the one Main
# Administrator). Uses Django's cache framework rather than a new model:
# no CACHES backend is configured in settings, so this transparently
# uses Django's built-in in-memory cache — no new dependency, no new
# migration, and it self-expires, so there's nothing to clean up.

TOTP_RATE_LIMIT_MAX_ATTEMPTS = 5
TOTP_RATE_LIMIT_WINDOW_SECONDS = 15 * 60  # 15 minutes


def _totp_rate_limit_key(user):
    return f"totp_failed_attempts:{user.pk}"


def is_totp_rate_limited(user):
    """True if this account has failed TOTP/backup-code verification too many times recently and should be temporarily blocked from trying again."""
    from django.core.cache import cache

    return cache.get(_totp_rate_limit_key(user), 0) >= TOTP_RATE_LIMIT_MAX_ATTEMPTS


def record_totp_failure(user):
    """Call after a failed TOTP/backup-code check. Extends the lockout window on each additional failure — persistent hammering keeps the door closed rather than the window quietly expiring mid-attack."""
    from django.core.cache import cache

    key = _totp_rate_limit_key(user)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, TOTP_RATE_LIMIT_WINDOW_SECONDS)
    return attempts


def clear_totp_rate_limit(user):
    """Call after a successful verification — a legitimate success resets the counter rather than leaving stale failures counted against future attempts."""
    from django.core.cache import cache

    cache.delete(_totp_rate_limit_key(user))
