# Generated by Django 3.2.5 on 2022-09-14 22:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0041_merge_0025_task_is_editable_0040_auto_20220716_1520'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]
