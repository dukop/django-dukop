# Generated by Django 2.1.8 on 2019-06-01 15:10
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('calendar', '0006_null_interval'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='description',
            field=models.TextField(blank=True, help_text="Enter details, which will be displayed on the event's own page. You can use Markdown.", verbose_name='description'),
        ),
        migrations.AlterField(
            model_name='eventtime',
            name='end',
            field=models.DateTimeField(blank=True, null=True, verbose_name='end'),
        ),
    ]
