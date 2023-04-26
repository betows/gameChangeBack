# Generated by Django 3.2.5 on 2021-11-24 21:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0006_auto_20211116_1102'),
        ('tasks', '0003_auto_20211124_1839'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='store',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='stores.store', verbose_name='Loja'),
            preserve_default=False,
        ),
    ]