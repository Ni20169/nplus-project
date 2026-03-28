from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0013_projectapproval_add_approval_code"),
    ]

    operations = [
        migrations.AlterField(
            model_name="counterparty",
            name="contact_phone",
            field=models.CharField(blank=True, max_length=255, verbose_name="联系电话"),
        ),
        migrations.AlterField(
            model_name="projectapproval",
            name="change_note",
            field=models.TextField(blank=True, verbose_name="修改说明"),
        ),
        migrations.AlterField(
            model_name="projectapproval",
            name="approve_note",
            field=models.TextField(blank=True, verbose_name="审批意见"),
        ),
    ]
