from django.db import migrations

from student.consts import STSURVE


def create_stsurve_role(apps, schema_editor):
    Role = apps.get_model("bsadmin", "Role")
    Role.objects.get_or_create(name=STSURVE)


def remove_stsurve_role(apps, schema_editor):
    Role = apps.get_model("bsadmin", "Role")
    Role.objects.filter(name=STSURVE).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("student", "0001_initial"),
        ("bsadmin", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_stsurve_role, remove_stsurve_role),
    ]
