# Generated by Django 5.2.3 on 2025-06-24 09:00

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('travel_planner', '0003_destination_owner'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='destination',
            name='owner',
        ),
        migrations.AddField(
            model_name='destination',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
    ]
