from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0019_replace_contract_manage_permissions"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userprofile",
            name="can_contract_manage",
        ),
    ]