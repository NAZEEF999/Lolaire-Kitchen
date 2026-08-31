from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_order_delivery_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivery_latitude',
            field=models.DecimalField(
                max_digits=9, decimal_places=6, null=True, blank=True,
                help_text="Best-effort geocode of delivery_address, used to plot the Track Order map. May be blank if geocoding failed or wasn't attempted."
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_longitude',
            field=models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True),
        ),
    ]
