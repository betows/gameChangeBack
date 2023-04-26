# Generated by Django 3.2.5 on 2022-06-09 14:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0026_alter_reason_description'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reason',
            name='user_task',
        ),
        migrations.AddField(
            model_name='usertask',
            name='reason',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='tasks.reason'),
        ),
        migrations.AlterField(
            model_name='reason',
            name='reason_choice',
            field=models.CharField(choices=[('p', 'pessoal'), ('t', 'transito'), ('c', 'clima'), ('a', 'automático'), ('o', 'outros')], max_length=1, null=True, verbose_name='Motivos'),
        ),
        migrations.AlterField(
            model_name='task',
            name='suggested_time',
            field=models.TimeField(blank=True, null=True, verbose_name='Hora sugerida'),
        ),
    ]