from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0005_userprofile_permissions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="can_view_project_list",
            field=models.BooleanField(default=False, verbose_name="可用-项目列表"),
        ),
    ]
