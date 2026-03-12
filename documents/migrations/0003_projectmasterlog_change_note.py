from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0002_userprofile"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectmasterlog",
            name="change_note",
            field=models.CharField(blank=True, max_length=200, verbose_name="修改说明"),
        ),
    ]
