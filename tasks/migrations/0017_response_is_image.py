# Generated by Django 3.2.5 on 2022-01-20 17:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0016_seencomment'),
    ]

    operations = [
        migrations.AddField(
            model_name='response',
            name='is_image',
            field=models.BooleanField(null=True, verbose_name='O arquivo é uma imagem?'),
        ),
    ]
