from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0004_projectmaster_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="can_approval_manage",
            field=models.BooleanField(default=False, verbose_name="可用-审批管理"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="can_create_project",
            field=models.BooleanField(default=False, verbose_name="可用-新增项目"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="can_query_project",
            field=models.BooleanField(default=True, verbose_name="可用-查询项目"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="can_update_project",
            field=models.BooleanField(default=False, verbose_name="可用-信息更新"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="can_user_manage",
            field=models.BooleanField(default=False, verbose_name="可用-用户管理"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="can_view_project_list",
            field=models.BooleanField(default=True, verbose_name="可用-项目列表"),
        ),
    ]
