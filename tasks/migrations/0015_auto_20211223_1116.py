# Generated by Django 3.2.5 on 2021-12-23 14:16

from django.db import migrations, models
import tasks.models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0014_auto_20211216_1731'),
    ]

    operations = [
        migrations.AddField(
            model_name='usertask',
            name='title_extension',
            field=models.CharField(blank=True, max_length=50, verbose_name='Extensão do título'),
        ),
        migrations.AlterField(
            model_name='response',
            name='file',
            field=models.FileField(null=True, upload_to=tasks.models.get_upload, verbose_name='Arquivo de upload'),
        ),
    ]