# Generated by Django 3.2.5 on 2021-11-30 15:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0006_auto_20211129_1630'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='category',
            options={'verbose_name': 'Categoria', 'verbose_name_plural': 'Categorias'},
        ),
        migrations.AlterModelOptions(
            name='group',
            options={'verbose_name': 'Grupo', 'verbose_name_plural': 'Grupos'},
        ),
    ]
