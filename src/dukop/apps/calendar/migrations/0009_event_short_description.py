# Generated by Django 2.2.17 on 2020-11-08 20:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendar', '0008_event_links'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='short_description',
            field=models.TextField(blank=True, help_text='A special short version of the event description, leave blank to auto-generate. Text-only, no Markdown.', verbose_name='short description'),
        ),
    ]
