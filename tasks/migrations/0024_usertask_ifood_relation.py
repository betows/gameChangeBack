# Generated by Django 3.2.5 on 2022-05-11 15:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ifood', '0027_auto_20220511_1155'),
        ('tasks', '0023_alter_task_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='usertask',
            name='ifood_relation',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='ifood.reviews'),
        ),
    ]
