# Generated by Django 3.2.5 on 2021-11-24 21:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='type',
            field=models.CharField(choices=[('f', 'file'), ('t', 'text'), ('s', 'simple')], max_length=1, verbose_name='Tipo de submissão'),
        ),
        migrations.AlterField(
            model_name='task',
            name='submission',
            field=models.OneToOneField(default=None, on_delete=django.db.models.deletion.CASCADE, to='tasks.submission', verbose_name='Submissão'),
            preserve_default=False,
        ),
    ]
