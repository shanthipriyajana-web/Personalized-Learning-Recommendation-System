from django.db import migrations, models


def activate_legacy_accounts(apps, schema_editor):
    """Approval is gone: PENDING accounts become ACTIVE, REJECTED become SUSPENDED."""
    User = apps.get_model('learning_system', 'User')
    User.objects.filter(status='PENDING').update(status='ACTIVE', is_active=True)
    User.objects.filter(status='REJECTED').update(status='SUSPENDED')


class Migration(migrations.Migration):

    dependencies = [
        ('learning_system', '0002_registrationapproval_user_and_more'),
    ]

    operations = [
        migrations.RunPython(activate_legacy_accounts, migrations.RunPython.noop),
        migrations.DeleteModel(name='RegistrationApproval'),
        migrations.AlterField(
            model_name='user',
            name='status',
            field=models.CharField(
                choices=[('ACTIVE', 'Active'), ('SUSPENDED', 'Suspended')],
                db_index=True, default='ACTIVE', max_length=20,
            ),
        ),
    ]
