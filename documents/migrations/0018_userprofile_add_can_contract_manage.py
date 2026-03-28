from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0017_alter_contractmaster_execution_project_code_snapshot_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="can_contract_manage",
            field=models.BooleanField(default=False, verbose_name="可用-合同管理"),
        ),
    ]
