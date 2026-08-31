from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_restaurantsettings_latitude_longitude'),
    ]

    operations = [
        migrations.AddField(
            model_name='restaurantsettings',
            name='twitter_url',
            field=models.URLField(blank=True, verbose_name='Twitter/X URL'),
        ),
        migrations.AddField(
            model_name='restaurantsettings',
            name='tiktok_url',
            field=models.URLField(blank=True, verbose_name='TikTok URL'),
        ),
    ]
