from django.db import migrations, models


def copy_contract_manage_permission(apps, schema_editor):
    UserProfile = apps.get_model("documents", "UserProfile")
    UserProfile.objects.filter(can_contract_manage=True).update(
        can_view_contract_ledger=True,
        can_edit_contract_adjustment=True,
        can_manage_counterparty=True,
    )


def reverse_copy_contract_manage_permission(apps, schema_editor):
    UserProfile = apps.get_model("documents", "UserProfile")
    UserProfile.objects.filter(
        can_view_contract_ledger=True,
        can_edit_contract_adjustment=True,
        can_manage_counterparty=True,
    ).update(can_contract_manage=True)


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0018_userprofile_add_can_contract_manage"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="can_edit_contract_adjustment",
            field=models.BooleanField(default=False, verbose_name="可用-合同调整"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="can_manage_counterparty",
            field=models.BooleanField(default=False, verbose_name="可用-往来单位管理"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="can_view_contract_ledger",
            field=models.BooleanField(default=False, verbose_name="可用-合同台账"),
        ),
        migrations.RunPython(copy_contract_manage_permission, reverse_copy_contract_manage_permission),
    ]