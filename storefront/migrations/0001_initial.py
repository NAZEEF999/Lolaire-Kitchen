from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ContactMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("full_name", models.CharField(max_length=150)),
                ("email", models.EmailField(max_length=254)),
                ("message", models.TextField()),
                ("is_read", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name": "Contact Message",
                "verbose_name_plural": "Contact Messages",
                "ordering": ["-created_at"],
            },
        ),
    ]
