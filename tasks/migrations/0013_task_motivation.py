# Generated by Django 3.2.5 on 2021-12-14 20:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0012_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='motivation',
            field=models.CharField(blank=True, max_length=500, verbose_name='Motivação'),
        ),
    ]
