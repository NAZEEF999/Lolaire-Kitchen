from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_restaurantsettings_auto_update_exchange_rate_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='restaurantsettings',
            name='latitude',
            field=models.DecimalField(
                max_digits=9, decimal_places=6, null=True, blank=True,
                help_text="Restaurant location for the Track Order map and Get Directions link. Look this up once on Google Maps (right-click the pin \u2192 copy coordinates)."
            ),
        ),
        migrations.AddField(
            model_name='restaurantsettings',
            name='longitude',
            field=models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True),
        ),
    ]
