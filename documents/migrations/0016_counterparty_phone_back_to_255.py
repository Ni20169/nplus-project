from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0015_expand_counterparty_phone_again"),
    ]

    operations = [
        # Truncate any existing values that exceed 255 chars before shrinking the column
        migrations.RunSQL(
            sql="UPDATE documents_counterparty SET contact_phone = LEFT(contact_phone, 255) WHERE LENGTH(contact_phone) > 255;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name="counterparty",
            name="contact_phone",
            field=models.CharField(blank=True, max_length=255, verbose_name="联系电话"),
        ),
    ]
