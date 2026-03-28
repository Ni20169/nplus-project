from django.db import migrations, models


def fill_approval_code(apps, schema_editor):
    ProjectApproval = apps.get_model("documents", "ProjectApproval")
    for item in ProjectApproval.objects.all().order_by("id"):
        if item.approval_code:
            continue
        submit_time = item.submit_time.strftime("%Y%m%d") if item.submit_time else "00000000"
        item.approval_code = f"AP{submit_time}{item.id:06d}"
        item.save(update_fields=["approval_code"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0012_contractmaster_add_execution_project_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectapproval",
            name="approval_code",
            field=models.CharField(blank=True, db_index=True, max_length=24, unique=True, verbose_name="审批编码"),
        ),
        migrations.RunPython(fill_approval_code, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="projectapproval",
            name="project_code",
            field=models.CharField(blank=True, default="", max_length=12, verbose_name="项目编码"),
        ),
    ]
