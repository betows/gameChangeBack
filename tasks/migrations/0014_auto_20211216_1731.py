# Generated by Django 3.2.5 on 2021-12-16 20:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0013_task_motivation'),
    ]

    operations = [
        migrations.AddField(
            model_name='usertask',
            name='concluded_by_user',
            field=models.BooleanField(default=True, verbose_name='Status modificado pelo usuário'),
        ),
        migrations.AlterField(
            model_name='periodicrelation',
            name='obs',
            field=models.CharField(blank=True, help_text='Utilize esse campo se quiser exibir uma descrição personalizada a este usuário', max_length=500, verbose_name='Observação'),
        ),
    ]
