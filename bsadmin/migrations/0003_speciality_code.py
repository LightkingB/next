# Generated by Django 4.2.19 on 2025-02-26 06:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bsadmin', '0002_alter_facultytranscript_unique_together_speciality'),
    ]

    operations = [
        migrations.AddField(
            model_name='speciality',
            name='code',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Шифр'),
        ),
    ]
