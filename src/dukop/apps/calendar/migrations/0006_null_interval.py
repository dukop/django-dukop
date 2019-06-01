# Generated by Django 2.1.8 on 2019-05-26 22:34
import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('calendar', '0005_auto_20190526_1640'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='interval',
            field=models.ForeignKey(blank=True, help_text='Repeats the event automatically at some interval', null=True, on_delete=django.db.models.deletion.PROTECT, to='calendar.Interval'),
        ),
    ]
