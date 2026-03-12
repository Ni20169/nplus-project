# Generated manually on 2026-03-13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0005_projectapproval"),
    ]

    operations = [
        # 修改 project_code 字段长度
        migrations.AlterField(
            model_name="projectapproval",
            name="project_code",
            field=models.CharField(max_length=50, verbose_name="项目编码"),
        ),
        # 添加 project_name 字段
        migrations.AddField(
            model_name="projectapproval",
            name="project_name",
            field=models.CharField(blank=True, max_length=200, verbose_name="项目名称"),
        ),
        # 修改 approval_type 字段选项
        migrations.AlterField(
            model_name="projectapproval",
            name="approval_type",
            field=models.CharField(
                choices=[("update", "修改"), ("delete", "删除"), ("import", "导入")],
                max_length=10,
                verbose_name="审批类型"
            ),
        ),
        # 添加 import_file_path 字段
        migrations.AddField(
            model_name="projectapproval",
            name="import_file_path",
            field=models.CharField(blank=True, max_length=500, verbose_name="导入文件路径"),
        ),
    ]
