# Generated by Django 3.2.5 on 2022-06-15 18:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0034_auto_20220614_1048'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supporting',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='supporting', to='tasks.task', verbose_name='Tarefa'),
        ),
    ]