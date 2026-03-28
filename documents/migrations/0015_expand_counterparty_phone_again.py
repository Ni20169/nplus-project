from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0014_expand_counterparty_phone_and_approval_notes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="counterparty",
            name="contact_phone",
            field=models.CharField(blank=True, max_length=510, verbose_name="联系电话"),
        ),
    ]
