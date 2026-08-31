import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import accounts.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0002_staffaccess"),
    ]

    operations = [
        migrations.CreateModel(
            name="StaffTag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=50, unique=True)),
            ],
            options={
                "verbose_name": "Staff Tag",
                "verbose_name_plural": "Staff Tags",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="user",
            name="account_status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("suspended", "Suspended"),
                    ("recovery_pending", "Recovery Pending"),
                    ("recovery_rejected", "Recovery Rejected"),
                ],
                default="active",
                help_text="Set only via accounts.services — see AccountStatus.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="totp_secret",
            field=models.CharField(blank=True, help_text="Base32 TOTP secret. Blank until 2FA is set up.", max_length=32),
        ),
        migrations.AddField(
            model_name="user",
            name="totp_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="tags",
            field=models.ManyToManyField(blank=True, related_name="staff_members", to="accounts.stafftag"),
        ),
        migrations.AddField(
            model_name="staffaccess",
            name="dashboard_actions",
            field=models.JSONField(
                default=accounts.models._default_actions,
                help_text="Per-module action-level ON/OFF for the Dashboard (view/create/edit/delete, only where meaningful — see MODULE_ACTIONS). Only takes effect where the matching dashboard_sections entry is also ON.",
            ),
        ),
        migrations.AddField(
            model_name="staffaccess",
            name="admin_actions",
            field=models.JSONField(
                default=accounts.models._default_actions,
                help_text="Per-module action-level ON/OFF for Django Admin. Only takes effect where the matching admin_sections entry is also ON.",
            ),
        ),
        migrations.CreateModel(
            name="AccountRecoveryRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.CharField(blank=True, max_length=255)),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_recovery_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recovery_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Account Recovery Request",
                "verbose_name_plural": "Account Recovery Requests",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="BackupCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code_hash", models.CharField(max_length=128)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="backup_codes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Backup Code",
                "verbose_name_plural": "Backup Codes",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AuditLogEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("permissions_changed", "Permissions changed"),
                            ("staff_activated", "Staff activated"),
                            ("staff_deactivated", "Staff deactivated"),
                            ("recovery_approved", "Recovery approved"),
                            ("recovery_rejected", "Recovery rejected"),
                            ("totp_enabled", "Two-factor authentication enabled"),
                        ],
                        max_length=30,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_actions_performed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "target_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_actions_received",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Audit Log Entry",
                "verbose_name_plural": "Audit Log Entries",
                "ordering": ["-created_at"],
            },
        ),
    ]
