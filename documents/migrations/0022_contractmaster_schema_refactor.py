import datetime
import django.db.models.deletion
from django.db import migrations, models


def clean_data_for_constraints(apps, schema_editor):
    """
    数据迁移：在添加 NOT NULL 和 UNIQUE 约束之前清理历史数据。
    1. sign_date 为空 → 填充为今日日期
    2. execution_project 为空 → 用 project 回填
    3. contract_no 为空 → 生成唯一占位值
    4. contract_no 重复 → 追加 -id 后缀
    """
    ContractMaster = apps.get_model("documents", "ContractMaster")
    today = datetime.date.today()

    # 1. 修复 sign_date 空值
    ContractMaster.objects.filter(sign_date__isnull=True).update(sign_date=today)

    # 2. 修复 execution_project 空值（用 project 回填）
    for contract in ContractMaster.objects.filter(execution_project__isnull=True).only(
        "id", "project_id", "execution_project_id"
    ):
        contract.execution_project_id = contract.project_id
        contract.save(update_fields=["execution_project_id"])

    # 3. 修复 contract_no 空值
    for contract in ContractMaster.objects.filter(contract_no="").only("id"):
        contract.contract_no = f"IMPORT-{contract.id}"
        contract.save(update_fields=["contract_no"])

    # 4. 修复 contract_no 重复值
    from django.db.models import Count

    dup_nos = (
        ContractMaster.objects.values("contract_no")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
        .values_list("contract_no", flat=True)
    )
    for dup_no in list(dup_nos):
        contracts = ContractMaster.objects.filter(contract_no=dup_no).order_by("id")
        for i, contract in enumerate(contracts[1:], start=1):
            contract.contract_no = f"{contract.contract_no}-{contract.id}"
            contract.save(update_fields=["contract_no"])


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0021_performance_indexes_for_counterparty_search"),
    ]

    operations = [
        # 1. 新增字段（安全操作，先做）
        migrations.AddField(
            model_name="contractmaster",
            name="last_adjustment_type",
            field=models.CharField(
                blank=True, max_length=20, verbose_name="最近一次调整类型"
            ),
        ),

        # 2. 删除不再需要的字段
        migrations.RemoveField(model_name="contractmaster", name="source_record_id"),
        migrations.RemoveField(model_name="contractmaster", name="source_contract_no"),
        migrations.RemoveField(model_name="contractmaster", name="effective_date"),
        migrations.RemoveField(model_name="contractmaster", name="close_date"),

        # 3. 安全删除旧命名索引（RemoveField 应已级联删除，IF EXISTS 保证幂等）
        migrations.RunSQL(
            sql="DROP INDEX IF EXISTS idx_contract_source_no;",
            reverse_sql="",
        ),

        # 4. 数据清理：在施加 NOT NULL / UNIQUE 约束之前修复历史脏数据
        migrations.RunPython(clean_data_for_constraints, migrations.RunPython.noop),

        # 5. 将 contract_year 从 VARCHAR(4) 转换为 SMALLINT
        #    先把空字符串置 NULL，再 CAST 为整数
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        UPDATE documents_contractmaster
                        SET contract_year = NULL
                        WHERE contract_year = '' OR contract_year IS NULL;

                        ALTER TABLE documents_contractmaster
                        ALTER COLUMN contract_year TYPE SMALLINT
                        USING CASE
                            WHEN contract_year ~ '^[0-9]{4}$' THEN contract_year::SMALLINT
                            ELSE NULL
                        END;
                    """,
                    reverse_sql="""
                        ALTER TABLE documents_contractmaster
                        ALTER COLUMN contract_year TYPE VARCHAR(4)
                        USING COALESCE(contract_year::TEXT, '');
                    """,
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="contractmaster",
                    name="contract_year",
                    field=models.PositiveSmallIntegerField(
                        null=True, verbose_name="合同年份"
                    ),
                ),
            ],
        ),

        # 6. execution_project 去除 null=True（加 NOT NULL 约束）
        migrations.AlterField(
            model_name="contractmaster",
            name="execution_project",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="execution_contracts",
                to="documents.projectmaster",
                verbose_name="对应执行层项目",
            ),
        ),

        # 7. sign_date 去除 null=True（加 NOT NULL 约束）
        migrations.AlterField(
            model_name="contractmaster",
            name="sign_date",
            field=models.DateField(verbose_name="签订日期"),
        ),

        # 8. contract_no 添加 UNIQUE 约束
        migrations.AlterField(
            model_name="contractmaster",
            name="contract_no",
            field=models.CharField(
                max_length=100, unique=True, verbose_name="合同编号"
            ),
        ),
    ]
