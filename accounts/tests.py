"""
Tests for the accounts app.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from . import selectors, services
from .models import StaffAccess, UserRole
from .validators import phone_number_validator, validate_role_change_allowed

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user_defaults_to_waiter_role(self):
        user = User.objects.create_user(username="waiter1", password="pass12345")
        self.assertEqual(user.role, UserRole.WAITER)
        self.assertTrue(user.is_waiter)
        self.assertFalse(user.is_staff)

    def test_create_superuser_defaults_to_administrator_role(self):
        user = User.objects.create_superuser(username="admin1", password="pass12345")
        self.assertEqual(user.role, UserRole.ADMINISTRATOR)
        self.assertTrue(user.is_administrator)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_manager_role_grants_staff_access(self):
        user = User.objects.create_user(username="mgr1", password="pass12345", role=UserRole.MANAGER)
        self.assertTrue(user.is_staff)

    def test_cashier_role_does_not_grant_staff_access(self):
        user = User.objects.create_user(username="cash1", password="pass12345", role=UserRole.CASHIER)
        self.assertFalse(user.is_staff)

    def test_str_returns_full_name_or_username(self):
        user = User.objects.create_user(
            username="wtest", password="pass12345", first_name="Ada", last_name="Obi"
        )
        self.assertEqual(str(user), "Ada Obi")


class ValidatorTests(TestCase):
    def test_valid_phone_numbers_pass(self):
        phone_number_validator("08012345678")
        phone_number_validator("+2348012345678")

    def test_invalid_phone_number_raises(self):
        with self.assertRaises(ValidationError):
            phone_number_validator("12345")

    def test_role_change_blocked_for_last_administrator(self):
        admin = User.objects.create_user(
            username="onlyadmin", password="pass12345", role=UserRole.ADMINISTRATOR
        )
        with self.assertRaises(ValidationError):
            validate_role_change_allowed(admin, UserRole.MANAGER)

    def test_role_change_allowed_when_another_administrator_exists(self):
        admin1 = User.objects.create_user(
            username="admin1", password="pass12345", role=UserRole.ADMINISTRATOR
        )
        User.objects.create_user(username="admin2", password="pass12345", role=UserRole.ADMINISTRATOR)
        validate_role_change_allowed(admin1, UserRole.MANAGER)  # should not raise


class SelectorTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="w1", password="pass12345", role=UserRole.WAITER)
        User.objects.create_user(username="c1", password="pass12345", role=UserRole.CASHIER)
        User.objects.create_user(username="m1", password="pass12345", role=UserRole.MANAGER)

    def test_get_users_by_role(self):
        self.assertEqual(selectors.get_waiters().count(), 1)
        self.assertEqual(selectors.get_cashiers().count(), 1)
        self.assertEqual(selectors.get_managers().count(), 1)
        self.assertEqual(selectors.get_administrators().count(), 0)

    def test_get_user_by_username(self):
        user = selectors.get_user_by_username("w1")
        self.assertIsNotNone(user)
        self.assertEqual(user.role, UserRole.WAITER)

    def test_get_user_by_username_missing_returns_none(self):
        self.assertIsNone(selectors.get_user_by_username("does-not-exist"))

    def test_get_active_users_excludes_inactive(self):
        User.objects.create_user(username="inactive1", password="pass12345", is_active=False)
        self.assertEqual(selectors.get_active_users().count(), 3)


class ServiceTests(TestCase):
    def test_create_staff_user(self):
        user = services.create_staff_user(
            username="newcashier", password="pass12345", role=UserRole.CASHIER, first_name="Tunde"
        )
        self.assertTrue(User.objects.filter(username="newcashier").exists())
        self.assertEqual(user.role, UserRole.CASHIER)

    def test_update_profile(self):
        user = User.objects.create_user(username="profiletest", password="pass12345")
        services.update_profile(user=user, first_name="New", phone_number="08012345678")
        user.refresh_from_db()
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.phone_number, "08012345678")

    def test_change_user_role_blocked_for_last_administrator(self):
        admin = User.objects.create_user(
            username="soleadmin", password="pass12345", role=UserRole.ADMINISTRATOR
        )
        with self.assertRaises(ValidationError):
            services.change_user_role(user=admin, new_role=UserRole.MANAGER)

    def test_change_user_role_succeeds_with_another_administrator(self):
        admin1 = User.objects.create_user(
            username="admin1b", password="pass12345", role=UserRole.ADMINISTRATOR
        )
        User.objects.create_user(username="admin2b", password="pass12345", role=UserRole.ADMINISTRATOR)
        services.change_user_role(user=admin1, new_role=UserRole.MANAGER)
        admin1.refresh_from_db()
        self.assertEqual(admin1.role, UserRole.MANAGER)

    def test_change_user_role_persists_is_staff_sync(self):
        """
        Regression test: change_user_role's save(update_fields=...) must
        include "is_staff", or the pre_save signal's is_staff change
        (sync_staff_status_with_role) is silently dropped from the SQL
        UPDATE and never reaches the database.
        """
        waiter = User.objects.create_user(username="promoteme", password="pass12345", role=UserRole.WAITER)
        self.assertFalse(waiter.is_staff)

        services.change_user_role(user=waiter, new_role=UserRole.MANAGER)
        waiter.refresh_from_db()
        self.assertEqual(waiter.role, UserRole.MANAGER)
        self.assertTrue(waiter.is_staff)

        services.change_user_role(user=waiter, new_role=UserRole.CASHIER)
        waiter.refresh_from_db()
        self.assertFalse(waiter.is_staff)


class AuthViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="logintest", password="pass12345", role=UserRole.WAITER)

    def test_login_page_loads(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)

    def test_login_success_redirects(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "logintest", "password": "pass12345"}
        )
        self.assertEqual(response.status_code, 302)

    def test_login_failure_reshows_form(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "logintest", "password": "wrongpass"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["user"].is_authenticated)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)

    def test_profile_accessible_when_logged_in(self):
        self.client.login(username="logintest", password="pass12345")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)

    def test_profile_update_via_view(self):
        self.client.login(username="logintest", password="pass12345")
        response = self.client.post(
            reverse("accounts:profile"),
            {"first_name": "Chidi", "last_name": "Eze", "email": "chidi@example.com", "phone_number": ""},
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Chidi")

    def test_logout_redirects_to_login(self):
        self.client.login(username="logintest", password="pass12345")
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))

    def test_change_password_requires_login(self):
        response = self.client.get(reverse("accounts:change_password"))
        self.assertEqual(response.status_code, 302)

    def test_password_reset_page_loads(self):
        response = self.client.get(reverse("accounts:password_reset"))
        self.assertEqual(response.status_code, 200)

    def test_password_reset_done_page_loads(self):
        response = self.client.get(reverse("accounts:password_reset_done"))
        self.assertEqual(response.status_code, 200)


class IsStaffSyncTests(TestCase):
    """
    Section 9 of the hardening pass: User.is_staff must track
    StaffAccess.admin_panel_enabled, not the legacy `role` field —
    see accounts/signals.py's sync_admin_panel_staff_flag.
    """

    def test_new_staffaccess_with_admin_panel_off_leaves_is_staff_false(self):
        user = User.objects.create_user(username="cashier1", password="pass12345", role=UserRole.CASHIER)
        StaffAccess.objects.create(user=user, admin_panel_enabled=False)
        user.refresh_from_db()
        self.assertFalse(user.is_staff)

    def test_admin_panel_enabled_true_sets_is_staff_true_regardless_of_role(self):
        """The exact contradiction this fix closes: a Cashier granted Admin Panel access must not be blocked by role."""
        user = User.objects.create_user(username="cashier2", password="pass12345", role=UserRole.CASHIER)
        access = StaffAccess.objects.create(user=user, admin_panel_enabled=False)
        self.assertFalse(User.objects.get(pk=user.pk).is_staff)

        access.admin_panel_enabled = True
        access.save()
        self.assertTrue(User.objects.get(pk=user.pk).is_staff)

    def test_administrator_role_with_admin_panel_off_has_is_staff_false(self):
        """The inverse case: role alone (even Administrator) no longer grants is_staff on its own."""
        user = User.objects.create_user(username="admin3", password="pass12345", role=UserRole.ADMINISTRATOR)
        StaffAccess.objects.create(user=user, admin_panel_enabled=False)
        user.refresh_from_db()
        self.assertFalse(user.is_staff)

    def test_superuser_is_staff_is_never_touched_by_staffaccess(self):
        superuser = User.objects.create_superuser(username="root1", password="pass12345")
        self.assertTrue(superuser.is_staff)
        StaffAccess.objects.create(user=superuser, admin_panel_enabled=False)
        superuser.refresh_from_db()
        self.assertTrue(superuser.is_staff)


class DjangoAdminActionLevelPermissionTests(TestCase):
    """
    Section 6 of the hardening pass: Django Admin's view/add/change
    /delete hooks must check the specific StaffAccess.admin_actions
    entry, not just whether the module itself is ON — see
    core/admin_mixins.py's ModulePermissionAdminMixin.
    """

    def setUp(self):
        self.client = Client()
        self.view_only = User.objects.create_user(username="viewonly1", password="pass12345", is_staff=True)
        StaffAccess.objects.create(
            user=self.view_only,
            admin_panel_enabled=True,
            admin_sections={"menu": True},
            admin_actions={"menu": {"view": True, "create": False, "edit": False, "delete": False}},
        )
        self.full_access = User.objects.create_user(username="fullaccess2", password="pass12345", is_staff=True)
        StaffAccess.objects.create(
            user=self.full_access,
            admin_panel_enabled=True,
            admin_sections={"menu": True},
            admin_actions={"menu": {"view": True, "create": True, "edit": True, "delete": True}},
        )

    def test_view_only_can_open_changelist(self):
        self.client.login(username="viewonly1", password="pass12345")
        response = self.client.get(reverse("admin:menu_menuitem_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_view_only_cannot_reach_add_page(self):
        """The exact bug this fix closes: previously module ON alone allowed add/change/delete regardless of the specific action toggle."""
        self.client.login(username="viewonly1", password="pass12345")
        response = self.client.get(reverse("admin:menu_menuitem_add"))
        self.assertEqual(response.status_code, 403)

    def test_full_access_can_reach_add_page(self):
        self.client.login(username="fullaccess2", password="pass12345")
        response = self.client.get(reverse("admin:menu_menuitem_add"))
        self.assertEqual(response.status_code, 200)


class UserAndStaffAccessAdminSuperuserOnlyTests(TestCase):
    """
    Sections 7 and 8 of the hardening pass: the raw User and
    StaffAccess Django Admin screens must be reachable only by the
    Main Administrator, regardless of any "staff" module grant — see
    accounts/admin.py and core/admin_mixins.SuperuserOnlyAdminMixin.
    """

    def setUp(self):
        self.client = Client()
        self.staff_module_granted = User.objects.create_user(
            username="staffgrant1", password="pass12345", is_staff=True
        )
        StaffAccess.objects.create(
            user=self.staff_module_granted,
            admin_panel_enabled=True,
            admin_sections={"staff": True},
            admin_actions={"staff": {"view": True}},
        )
        self.superuser = User.objects.create_superuser(username="root2", password="pass12345")

    def test_staff_module_grant_cannot_open_user_admin(self):
        """The exact bug this fix closes: granting the "staff" module used to be enough to reach raw User/StaffAccess admin screens."""
        self.client.login(username="staffgrant1", password="pass12345")
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 403)

    def test_staff_module_grant_cannot_open_staffaccess_admin(self):
        self.client.login(username="staffgrant1", password="pass12345")
        response = self.client.get(reverse("admin:accounts_staffaccess_changelist"))
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_open_user_admin(self):
        self.client.login(username="root2", password="pass12345")
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        self.assertEqual(response.status_code, 200)

    def test_superuser_cannot_strip_own_is_superuser_via_admin_form(self):
        """A narrower edge case beyond the main fix: the one Super Admin editing their own account shouldn't be able to accidentally self-lock via this raw form. Django Admin's readonly_fields removes a field from the editable form entirely (rendered as static text instead) rather than merely disabling it — so the correct check is that it's absent from the form's editable fields."""
        self.client.login(username="root2", password="pass12345")
        response = self.client.get(reverse("admin:accounts_user_change", args=[self.superuser.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("is_superuser", response.context["adminform"].form.fields)
        self.assertNotIn("is_active", response.context["adminform"].form.fields)


class StaffManagementSuperuserOnlyTests(TestCase):
    """
    Sections 10 and 11 of the hardening pass: every Staff Management
    view requires is_superuser directly — granting the "staff"
    StaffAccess module must never be sufficient on its own, since
    Staff Management is a security-sensitive administrative function,
    not an ordinary operational module.
    """

    def setUp(self):
        self.client = Client()
        self.staff_module_granted = User.objects.create_user(username="staffgrant2", password="pass12345")
        StaffAccess.objects.create(
            user=self.staff_module_granted,
            dashboard_enabled=True,
            dashboard_sections={"staff": True},
            dashboard_actions={"staff": {"view": True}},
        )
        self.superuser = User.objects.create_superuser(username="root3", password="pass12345")

    def test_staff_module_grant_cannot_reach_staff_list(self):
        self.client.login(username="staffgrant2", password="pass12345")
        response = self.client.get(reverse("dashboard:staff_list"))
        self.assertEqual(response.status_code, 302)  # redirected to accounts:no_access

    def test_staff_module_grant_cannot_reach_staff_security(self):
        self.client.login(username="staffgrant2", password="pass12345")
        response = self.client.get(reverse("dashboard:staff_security"))
        self.assertEqual(response.status_code, 302)

    def test_staff_module_grant_cannot_reach_audit_log(self):
        self.client.login(username="staffgrant2", password="pass12345")
        response = self.client.get(reverse("dashboard:audit_log"))
        self.assertEqual(response.status_code, 302)

    def test_superuser_can_reach_staff_list(self):
        self.client.login(username="root3", password="pass12345")
        response = self.client.get(reverse("dashboard:staff_list"))
        self.assertEqual(response.status_code, 200)


class SuperAdminSelfLockoutTests(TestCase):
    """Section 27 of the hardening pass — preserved and explicitly tested, not just assumed."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(username="root4", password="pass12345")

    def test_superuser_cannot_suspend_self(self):
        with self.assertRaises(ValueError):
            services.suspend_account(actor=self.superuser, member=self.superuser)

    def test_non_superuser_cannot_suspend_superuser(self):
        actor = User.objects.create_user(username="someone1", password="pass12345")
        with self.assertRaises(ValueError):
            services.suspend_account(actor=actor, member=self.superuser)


class DuplicateRecoveryRequestTests(TestCase):
    """Section 26 of the hardening pass — one active pending recovery request per account."""

    def setUp(self):
        self.user = User.objects.create_user(username="recover1", password="pass12345")

    def test_repeated_reset_reuses_pending_request_instead_of_duplicating(self):
        from .models import AccountRecoveryRequest, RecoveryRequestStatus

        first = services.complete_password_reset(user=self.user)
        second = services.complete_password_reset(user=self.user)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            AccountRecoveryRequest.objects.filter(user=self.user, status=RecoveryRequestStatus.PENDING).count(), 1
        )

    def test_suspended_account_reset_creates_no_recovery_request(self):
        from .models import AccountRecoveryRequest, AccountStatus

        self.user.account_status = AccountStatus.SUSPENDED
        self.user.is_active = False
        self.user.save(update_fields=["account_status", "is_active"])

        result = services.complete_password_reset(user=self.user)
        self.assertIsNone(result)
        self.assertEqual(AccountRecoveryRequest.objects.filter(user=self.user).count(), 0)
        self.user.refresh_from_db()
        self.assertEqual(self.user.account_status, AccountStatus.SUSPENDED)


class TOTPRateLimitTests(TestCase):
    """Section 24 of the hardening pass — a 6-digit code has only 1,000,000 possibilities, so repeated failures must eventually block further attempts."""

    def setUp(self):
        self.user = User.objects.create_superuser(username="root5", password="pass12345")

    def test_not_rate_limited_initially(self):
        self.assertFalse(services.is_totp_rate_limited(self.user))

    def test_rate_limited_after_max_failures(self):
        for _ in range(services.TOTP_RATE_LIMIT_MAX_ATTEMPTS):
            services.record_totp_failure(self.user)
        self.assertTrue(services.is_totp_rate_limited(self.user))

    def test_clear_rate_limit_resets_counter(self):
        for _ in range(services.TOTP_RATE_LIMIT_MAX_ATTEMPTS):
            services.record_totp_failure(self.user)
        services.clear_totp_rate_limit(self.user)
        self.assertFalse(services.is_totp_rate_limited(self.user))

    def test_rate_limit_is_per_account(self):
        other_user = User.objects.create_superuser(username="root6", password="pass12345")
        for _ in range(services.TOTP_RATE_LIMIT_MAX_ATTEMPTS):
            services.record_totp_failure(self.user)
        self.assertTrue(services.is_totp_rate_limited(self.user))
        self.assertFalse(services.is_totp_rate_limited(other_user))
