from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_order_confirmation_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivery_address',
            field=models.TextField(
                blank=True,
                help_text="Only set for storefront delivery orders \u2014 blank for dine-in/table orders."
            ),
        ),
    ]
