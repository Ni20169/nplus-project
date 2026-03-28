# Generated manually for execution project mapping fields on ContractMaster

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0011_counterparty_add_extra_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="contractmaster",
            name="execution_project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="execution_contracts",
                to="documents.projectmaster",
                verbose_name="对应执行层项目",
            ),
        ),
        migrations.AddField(
            model_name="contractmaster",
            name="execution_project_code_snapshot",
            field=models.CharField(blank=True, default="", max_length=12, verbose_name="执行层项目编码快照"),
        ),
        migrations.AddField(
            model_name="contractmaster",
            name="execution_project_name_snapshot",
            field=models.CharField(blank=True, default="", max_length=100, verbose_name="执行层项目名称快照"),
        ),
    ]
