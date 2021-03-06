# Generated by Django 2.2.17 on 2021-01-31 22:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendar', '0011_link_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Sphere',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('slug', models.SlugField(blank=True, help_text='The part of a URL that is displayed in dukop.dk/sphere/<slug>/', null=True, verbose_name='slug')),
                ('default', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Sphere',
                'verbose_name_plural': 'Spheres',
                'ordering': ('-default', 'name'),
            },
        ),
        migrations.AddField(
            model_name='event',
            name='spheres',
            field=models.ManyToManyField(blank=True, to='calendar.Sphere'),
        ),
    ]
