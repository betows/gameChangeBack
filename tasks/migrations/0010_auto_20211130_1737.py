# Generated by Django 3.2.5 on 2021-11-30 20:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0009_auto_20211130_1658'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='submission',
            name='task',
        ),
        migrations.AddField(
            model_name='task',
            name='submission',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='tasks.submission', verbose_name='Tarefa'),
            preserve_default=False,
        ),
    ]
