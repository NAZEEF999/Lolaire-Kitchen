from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_recovery_totp_audit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditlogentry",
            name="action",
            field=models.CharField(
                choices=[
                    ("permissions_changed", "Permissions changed"),
                    ("staff_activated", "Staff activated"),
                    ("staff_deactivated", "Staff deactivated"),
                    ("recovery_requested", "Recovery requested"),
                    ("recovery_approved", "Recovery approved"),
                    ("recovery_rejected", "Recovery rejected"),
                    ("recovery_blocked", "Recovery blocked (account suspended)"),
                    ("totp_enabled", "Two-factor authentication enabled"),
                ],
                max_length=30,
            ),
        ),
    ]
