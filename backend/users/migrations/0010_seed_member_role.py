from django.db import migrations


MEMBER_ROLE_NAME = 'Member'
MEMBER_ROLE_DESCRIPTION = 'Default role for staff login accounts created from the employee directory.'


def seed_member_role(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    Role.objects.get_or_create(
        name=MEMBER_ROLE_NAME,
        defaults={'description': MEMBER_ROLE_DESCRIPTION, 'is_active': True},
    )


def remove_member_role(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    Role.objects.filter(name=MEMBER_ROLE_NAME).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_erpemployeerecord'),
    ]

    operations = [
        migrations.RunPython(seed_member_role, remove_member_role),
    ]
