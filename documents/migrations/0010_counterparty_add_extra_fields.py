# Generated migration for adding 8 new fields to Counterparty

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0009_counterparty_contractmaster_contractadjustment_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='counterparty',
            name='established_date',
            field=models.DateField(blank=True, null=True, verbose_name='成立日期'),
        ),
        migrations.AddField(
            model_name='counterparty',
            name='province_code',
            field=models.CharField(blank=True, max_length=6, verbose_name='所属省份'),
        ),
        migrations.AddField(
            model_name='counterparty',
            name='city',
            field=models.CharField(blank=True, max_length=100, verbose_name='所属城市'),
        ),
        migrations.AddField(
            model_name='counterparty',
            name='enterprise_type',
            field=models.CharField(blank=True, max_length=100, verbose_name='企业类型'),
        ),
        migrations.AddField(
            model_name='counterparty',
            name='industry',
            field=models.CharField(blank=True, max_length=100, verbose_name='所属行业'),
        ),
        migrations.AddField(
            model_name='counterparty',
            name='former_name',
            field=models.CharField(blank=True, max_length=200, verbose_name='曾用名'),
        ),
        migrations.AddField(
            model_name='counterparty',
            name='registration_address',
            field=models.CharField(blank=True, max_length=500, verbose_name='注册地址'),
        ),
        migrations.AddField(
            model_name='counterparty',
            name='business_scope',
            field=models.TextField(blank=True, verbose_name='经营范围'),
        ),
    ]
