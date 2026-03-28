from decimal import Decimal

from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


PJ_CODE_REGEX = r"^PJ\d{10}$"
CT_CODE_REGEX = r"^CT\d{12}$"

SOURCE_SYSTEM_CHOICES = (
    ("SUBCONTRACT", "分包系统"),
    ("SUPPLYCHAIN", "供应链系统"),
    ("ZHZZ", "智慧中咨系统"),
    ("PROJECT", "项管系统"),
    ("MANUAL", "手工录入"),
)

CONTRACT_DIRECTION_CHOICES = (
    ("INCOME", "收入合同"),
    ("EXPENSE", "支出合同"),
    ("NONE", "无收出合同"),
)

CONTRACT_CATEGORY_CHOICES = (
    ("MAIN", "主合同"),
    ("SUBCONTRACT", "分包合同"),
    ("PURCHASE", "采购合同"),
    ("SERVICE", "服务合同"),
    ("OTHER", "其他"),
)

CONTRACT_STATUS_CHOICES = (
    ("DRAFT", "草稿"),
    ("SIGNED", "已签订"),
    ("ACTIVE", "履约中"),
    ("CLOSED", "已完结"),
    ("TERMINATED", "已终止"),
)

PARTY_TYPE_CHOICES = (
    ("OWNER", "业主"),
    ("SUPPLIER", "供应商"),
    ("SUBCONTRACTOR", "分包商"),
    ("SUPPLY_SUB", "供应&分包商"),
    ("OTHER_VENDOR", "其他外委单位"),
)

ADJUSTMENT_TYPE_CHOICES = (
    ("SUPPLEMENT", "补充合同/补充协议"),
    ("FINAL_SETTLEMENT", "最终结算"),
    ("MANUAL_CORRECTION", "手工修正"),
    ("OTHER", "其他"),
)

APPROVAL_STATUS_CHOICES = (
    ("DRAFT", "草稿"),
    ("IN_REVIEW", "审批中"),
    ("APPROVED", "审批通过"),
    ("RETURNED", "退回"),
)

ACTION_TYPE_CHOICES = (
    ("SUBMIT", "提交"),
    ("APPROVE", "通过"),
    ("RETURN", "退回"),
    ("EDIT", "修改"),
)


class DictType(models.Model):
    code = models.CharField("字典类型编码", max_length=50, unique=True)
    name = models.CharField("字典类型名称", max_length=100)
    group = models.CharField("字典分组", max_length=50, blank=True)
    description = models.TextField("说明", blank=True)
    is_active = models.BooleanField("是否启用", default=True)
    sort_order = models.PositiveIntegerField("排序", default=0)
    version = models.CharField("版本", max_length=20, blank=True)
    effective_start = models.DateField("生效开始日期", null=True, blank=True)
    effective_end = models.DateField("生效结束日期", null=True, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "字典类型"
        verbose_name_plural = "字典类型"
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class DictItem(models.Model):
    dict_type = models.ForeignKey(
        DictType,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="字典类型",
    )
    code = models.CharField("字典项编码", max_length=50)
    name = models.CharField("字典项名称", max_length=100)
    value = models.CharField("字典项值", max_length=200, blank=True)
    parent_code = models.CharField("上级编码", max_length=50, blank=True)
    is_active = models.BooleanField("是否启用", default=True)
    sort_order = models.PositiveIntegerField("排序", default=0)
    version = models.CharField("版本", max_length=20, blank=True)
    effective_start = models.DateField("生效开始日期", null=True, blank=True)
    effective_end = models.DateField("生效结束日期", null=True, blank=True)
    remark = models.CharField("备注", max_length=500, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "字典项"
        verbose_name_plural = "字典项"
        ordering = ["dict_type", "sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["dict_type", "code"], name="uniq_dict_type_code"
            ),
        ]

    def __str__(self):
        return f"{self.dict_type.code}:{self.code}-{self.name}"


class ImportBatch(models.Model):
    batch_no = models.CharField("导入批次号", max_length=50, unique=True)
    source_file = models.CharField("导入文件名", max_length=200)
    imported_by = models.CharField("导入人", max_length=50)
    imported_at = models.DateTimeField("导入时间", auto_now_add=True)
    total_count = models.PositiveIntegerField("总行数", default=0)
    success_count = models.PositiveIntegerField("成功数", default=0)
    fail_count = models.PositiveIntegerField("失败数", default=0)
    remark = models.CharField("备注", max_length=500, blank=True)

    class Meta:
        verbose_name = "导入批次"
        verbose_name_plural = "导入批次"
        ordering = ["-imported_at"]

    def __str__(self):
        return self.batch_no


class ImportError(models.Model):
    batch = models.ForeignKey(
        ImportBatch, on_delete=models.CASCADE, related_name="errors", verbose_name="导入批次"
    )
    row_number = models.PositiveIntegerField("行号")
    field_name = models.CharField("字段名", max_length=50, blank=True)
    error_message = models.CharField("错误原因", max_length=500)
    raw_data = models.JSONField("原始数据", null=True, blank=True)
    created_at = models.DateTimeField("记录时间", auto_now_add=True)

    class Meta:
        verbose_name = "导入错误"
        verbose_name_plural = "导入错误"
        ordering = ["row_number"]

    def __str__(self):
        return f"{self.batch.batch_no} - 第{self.row_number}行"


class ProjectMaster(models.Model):
    project_code = models.CharField(
        "项目主数据编码",
        max_length=12,
        unique=True,
        validators=[RegexValidator(PJ_CODE_REGEX, "项目编号必须为PJ开头的12位编码")],
    )
    project_name = models.CharField("项目名称", max_length=100, unique=True)
    org_name = models.CharField("项目机构名称", max_length=50)
    parent_pj_code = models.CharField("上级PJ编码", max_length=12, blank=True, null=True)
    province_code = models.CharField("所在省", max_length=6)
    city_code = models.CharField("所在市", max_length=6)
    business_unit = models.CharField("业务板块", max_length=50)
    dept = models.CharField("项目承担部门", max_length=50)
    project_type = models.CharField("项目类型", max_length=50)
    org_mode = models.CharField("项目组织模式", max_length=50)
    data_status = models.CharField("主数据系统数据状态", max_length=50)
    is_execution_level = models.BooleanField("是否为执行层", default=False)
    project_year = models.CharField("项目年份", max_length=4)
    status = models.CharField("状态", max_length=10, default="启用")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    created_by = models.CharField("创建人", max_length=50)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    updated_by = models.CharField("更新人", max_length=50)
    remark = models.TextField("备注", blank=True)
    is_deleted = models.BooleanField("是否删除", default=False)
    data_version = models.PositiveIntegerField("数据版本", default=1)

    class Meta:
        verbose_name = "项目主数据"
        verbose_name_plural = "项目主数据"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.project_code and len(self.project_code) >= 6:
            self.project_year = self.project_code[2:6]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.project_code} - {self.project_name}"


class ProjectMasterLog(models.Model):
    ACTION_CHOICES = (
        ("create", "新增"),
        ("update", "变更"),
        ("delete", "删除"),
        ("import", "导入"),
    )

    project_code = models.CharField("项目编码", max_length=12)
    action = models.CharField("动作", max_length=10, choices=ACTION_CHOICES)
    before_data = models.JSONField("修改前", null=True, blank=True)
    after_data = models.JSONField("修改后", null=True, blank=True)
    change_note = models.CharField("修改说明", max_length=200, blank=True)
    operator = models.CharField("操作人", max_length=50)
    source = models.CharField("来源", max_length=50, blank=True)
    created_at = models.DateTimeField("记录时间", auto_now_add=True)

    class Meta:
        verbose_name = "项目主数据日志"
        verbose_name_plural = "项目主数据日志"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project_code} - {self.action}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    department = models.CharField("部门", max_length=100, blank=True)
    can_user_manage = models.BooleanField("可用-用户管理", default=False)
    can_create_project = models.BooleanField("可用-新增项目", default=False)
    can_query_project = models.BooleanField("可用-查询项目", default=True)
    can_update_project = models.BooleanField("可用-信息更新", default=False)
    can_view_project_list = models.BooleanField("可用-项目列表", default=False)
    can_approval_manage = models.BooleanField("可用-审批管理", default=False)

    class Meta:
        verbose_name = "用户扩展信息"
        verbose_name_plural = "用户扩展信息"

    def __str__(self):
        return f"{self.user.username} - {self.department}"


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if not hasattr(instance, "profile"):
            UserProfile.objects.create(user=instance)


class ProjectApproval(models.Model):
    """项目修改/删除审批表"""
    APPROVAL_TYPE_CHOICES = (
        ("update", "修改"),
        ("delete", "删除"),
        ("import", "导入"),
        ("export", "导出"),
    )
    STATUS_CHOICES = (
        ("pending", "待审批"),
        ("approved", "已通过"),
        ("rejected", "已拒绝"),
    )

    project_code = models.CharField("项目编码", max_length=12)
    project_name = models.CharField("项目名称", max_length=200, blank=True)
    approval_type = models.CharField("审批类型", max_length=10, choices=APPROVAL_TYPE_CHOICES)
    before_data = models.JSONField("修改前数据", null=True, blank=True)
    after_data = models.JSONField("修改后数据", null=True, blank=True)
    change_note = models.CharField("修改说明", max_length=200, blank=True)
    submitter = models.CharField("提交人", max_length=50)
    approver = models.CharField("审批人", max_length=50, default="倪明珠")
    status = models.CharField("审批状态", max_length=10, choices=STATUS_CHOICES, default="pending")
    submit_time = models.DateTimeField("提交时间", auto_now_add=True)
    approve_time = models.DateTimeField("审批时间", null=True, blank=True)
    approve_note = models.CharField("审批意见", max_length=200, blank=True)
    import_file_path = models.CharField("导入文件路径", max_length=500, blank=True)

    class Meta:
        verbose_name = "项目审批"
        verbose_name_plural = "项目审批"
        ordering = ["-submit_time"]

    def __str__(self):
        return f"{self.project_code} - {self.get_approval_type_display()} - {self.get_status_display()}"


# -------------------------
# 公开博客模型
# -------------------------

class Tag(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField("标签名", max_length=50, unique=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "标签"
        verbose_name_plural = "标签"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Article(models.Model):
    id = models.BigAutoField(primary_key=True)
    TYPE_CHOICES = (("note", "学习笔记"), ("essay", "日常随笔"))

    article_type = models.CharField("类型", max_length=10, choices=TYPE_CHOICES)
    title = models.CharField("标题", max_length=200)
    content = models.TextField("正文（Markdown）")
    category = models.CharField("分类", max_length=50, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="标签")
    is_published = models.BooleanField("是否发布", default=False)
    published_at = models.DateTimeField("发布时间", null=True, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "文章"
        verbose_name_plural = "文章"
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title


class Counterparty(models.Model):
    id = models.BigAutoField(primary_key=True)
    party_name = models.CharField("单位名称", max_length=200)
    party_type = models.CharField("单位类型", max_length=20, choices=PARTY_TYPE_CHOICES)
    credit_code = models.CharField("统一社会信用代码", max_length=18, unique=True)
    contact_name = models.CharField("联系人", max_length=50, blank=True)
    contact_phone = models.CharField("联系电话", max_length=30, blank=True)
    status = models.CharField("状态", max_length=20, default="ACTIVE")
    remark = models.CharField("备注", max_length=500, blank=True)
    established_date = models.DateField("成立日期", null=True, blank=True)
    province_code = models.CharField("所属省份", max_length=6, blank=True)
    city = models.CharField("所属城市", max_length=100, blank=True)
    enterprise_type = models.CharField("企业类型", max_length=100, blank=True)
    industry = models.CharField("所属行业", max_length=100, blank=True)
    former_name = models.CharField("曾用名", max_length=200, blank=True)
    registration_address = models.CharField("注册地址", max_length=500, blank=True)
    business_scope = models.TextField("经营范围", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    created_by = models.CharField("创建人", max_length=50, blank=True, default="")
    updated_by = models.CharField("更新人", max_length=50, blank=True, default="")

    class Meta:
        verbose_name = "往来单位"
        verbose_name_plural = "往来单位"
        ordering = ["party_name"]
        indexes = [
            models.Index(fields=["party_name"], name="idx_counterparty_name"),
        ]

    def __str__(self):
        return f"{self.party_name} ({self.credit_code})"


class ContractMaster(models.Model):
    id = models.BigAutoField(primary_key=True)
    project = models.ForeignKey(
        ProjectMaster,
        on_delete=models.PROTECT,
        related_name="contracts",
        verbose_name="所属项目",
    )
    execution_project = models.ForeignKey(
        ProjectMaster,
        on_delete=models.PROTECT,
        related_name="execution_contracts",
        verbose_name="对应执行层项目",
        null=True,
        blank=True,
    )
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.PROTECT,
        related_name="contracts",
        verbose_name="签约相对方",
    )

    project_code_snapshot = models.CharField("项目主数据编码快照", max_length=12)
    execution_project_code_snapshot = models.CharField("执行层项目编码快照", max_length=12, blank=True)
    execution_project_name_snapshot = models.CharField("执行层项目名称快照", max_length=100, blank=True)
    contract_ct_code = models.CharField(
        "合同CT码",
        max_length=14,
        unique=True,
        validators=[RegexValidator(CT_CODE_REGEX, "CT码格式必须为CT+12位数字")],
    )

    contract_name = models.CharField("合同名称", max_length=200)
    contract_no = models.CharField("合同编号", max_length=100, blank=True)
    source_system = models.CharField("来源系统", max_length=20, choices=SOURCE_SYSTEM_CHOICES)
    source_record_id = models.CharField("来源记录ID", max_length=100, blank=True)
    source_contract_no = models.CharField("来源合同编号", max_length=100, blank=True)

    contract_direction = models.CharField("合同方向", max_length=20, choices=CONTRACT_DIRECTION_CHOICES)
    contract_category = models.CharField("合同分类", max_length=20, choices=CONTRACT_CATEGORY_CHOICES)
    undertaking_dept_code = models.CharField("承担部门编码", max_length=50, blank=True)
    undertaking_dept_name = models.CharField("承担部门名称", max_length=100, blank=True)
    contract_year = models.CharField("合同年份", max_length=4, blank=True)
    counterparty_name_snapshot = models.CharField("签约方名称快照", max_length=200)

    sign_date = models.DateField("签订日期", null=True, blank=True)
    effective_date = models.DateField("生效日期", null=True, blank=True)
    close_date = models.DateField("完结日期", null=True, blank=True)

    original_amount_tax = models.DecimalField("原始含税金额", max_digits=18, decimal_places=2, default=Decimal("0.00"))
    original_amount_notax = models.DecimalField("原始不含税金额", max_digits=18, decimal_places=2, default=Decimal("0.00"))
    original_tax_rate = models.DecimalField("原始税率", max_digits=5, decimal_places=4, null=True, blank=True)

    current_amount_tax = models.DecimalField("当前含税金额", max_digits=18, decimal_places=2, default=Decimal("0.00"))
    current_amount_notax = models.DecimalField("当前不含税金额", max_digits=18, decimal_places=2, default=Decimal("0.00"))
    current_tax_rate = models.DecimalField("当前税率", max_digits=5, decimal_places=4, null=True, blank=True)

    approved_adjustment_count = models.PositiveIntegerField("已通过调整次数", default=0)
    last_adjustment_date = models.DateField("最近一次已通过调整日期", null=True, blank=True)

    contract_status = models.CharField("合同状态", max_length=20, choices=CONTRACT_STATUS_CHOICES, default="SIGNED")
    remark = models.CharField("备注", max_length=500, blank=True)
    is_deleted = models.BooleanField("是否删除", default=False)
    data_version = models.PositiveIntegerField("数据版本", default=1)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    created_by = models.CharField("创建人", max_length=50, blank=True, default="")
    updated_by = models.CharField("更新人", max_length=50, blank=True, default="")

    class Meta:
        verbose_name = "合同主表"
        verbose_name_plural = "合同主表"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project"], name="idx_contract_project"),
            models.Index(fields=["counterparty"], name="idx_contract_counterparty"),
            models.Index(fields=["source_system"], name="idx_contract_source"),
            models.Index(fields=["contract_direction"], name="idx_contract_direction"),
            models.Index(fields=["contract_category"], name="idx_contract_category"),
            models.Index(fields=["contract_status"], name="idx_contract_status"),
            models.Index(fields=["undertaking_dept_code"], name="idx_contract_dept"),
            models.Index(fields=["contract_year"], name="idx_contract_year"),
            models.Index(fields=["project_code_snapshot"], name="idx_contract_proj_snapshot"),
            models.Index(fields=["project", "contract_direction"], name="idx_contract_proj_dir"),
            models.Index(fields=["project", "contract_category"], name="idx_contract_proj_cat"),
            models.Index(fields=["undertaking_dept_code", "contract_year"], name="idx_contract_dept_year"),
            models.Index(fields=["project", "contract_year"], name="idx_contract_proj_year"),
            models.Index(fields=["source_system", "source_contract_no"], name="idx_contract_source_no"),
        ]

    def clean(self):
        if self.current_amount_tax < 0 or self.current_amount_notax < 0:
            raise ValidationError("当前金额不允许为负值")
        if self.original_amount_tax < 0 or self.original_amount_notax < 0:
            raise ValidationError("原始金额不允许为负值")

    def save(self, *args, **kwargs):
        self.project_code_snapshot = self.project.project_code
        if self.execution_project_id:
            self.execution_project_code_snapshot = self.execution_project.project_code
            self.execution_project_name_snapshot = self.execution_project.project_name
        else:
            self.execution_project_code_snapshot = ""
            self.execution_project_name_snapshot = ""
        self.counterparty_name_snapshot = self.counterparty.party_name
        dept_source = self.execution_project if self.execution_project_id else self.project
        dept_name = dept_source.dept or ""
        if dept_source and dept_source.dept:
            dept_type = DictType.objects.filter(code="DEPT", is_active=True).prefetch_related("items").first()
            if dept_type:
                dept_name = next(
                    (item.name for item in dept_type.items.all() if item.code == dept_source.dept and item.is_active),
                    dept_source.dept,
                )
        self.undertaking_dept_name = dept_name
        self.undertaking_dept_code = ""
        if not self.contract_year and self.sign_date:
            self.contract_year = str(self.sign_date.year)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.contract_ct_code} - {self.contract_name}"


class ContractAdjustment(models.Model):
    id = models.BigAutoField(primary_key=True)
    contract = models.ForeignKey(
        ContractMaster,
        on_delete=models.CASCADE,
        related_name="adjustments",
        verbose_name="合同",
    )
    project = models.ForeignKey(
        ProjectMaster,
        on_delete=models.PROTECT,
        related_name="contract_adjustments",
        verbose_name="项目",
    )

    project_code_snapshot = models.CharField("项目主数据编码快照", max_length=12)
    contract_ct_code_snapshot = models.CharField("合同CT码快照", max_length=14)
    contract_name_snapshot = models.CharField("合同名称快照", max_length=200)

    adjustment_type = models.CharField("调整类型", max_length=20, choices=ADJUSTMENT_TYPE_CHOICES)
    adjustment_no = models.CharField("调整单号", max_length=100)
    adjustment_date = models.DateField("调整日期")
    effective_date = models.DateField("生效日期", null=True, blank=True)

    before_amount_tax = models.DecimalField("调整前含税金额", max_digits=18, decimal_places=2, default=Decimal("0.00"))
    before_amount_notax = models.DecimalField("调整前不含税金额", max_digits=18, decimal_places=2, default=Decimal("0.00"))
    before_tax_rate = models.DecimalField("调整前税率", max_digits=5, decimal_places=4, null=True, blank=True)
    before_counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="before_adjustments",
        verbose_name="调整前签约方",
    )
    before_counterparty_name = models.CharField("调整前签约方名称", max_length=200, blank=True)

    change_amount_tax = models.DecimalField("本次含税调整金额", max_digits=18, decimal_places=2, default=Decimal("0.00"))
    change_amount_notax = models.DecimalField("本次不含税调整金额", max_digits=18, decimal_places=2, default=Decimal("0.00"))
    after_tax_rate = models.DecimalField("调整后税率", max_digits=5, decimal_places=4, null=True, blank=True)
    after_counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="after_adjustments",
        verbose_name="调整后签约方",
    )
    remark = models.CharField("备注", max_length=500, blank=True)

    after_amount_tax = models.DecimalField("调整后含税金额", max_digits=18, decimal_places=2, default=Decimal("0.00"))
    after_amount_notax = models.DecimalField("调整后不含税金额", max_digits=18, decimal_places=2, default=Decimal("0.00"))
    after_counterparty_name = models.CharField("调整后签约方名称", max_length=200, blank=True)

    approval_status = models.CharField("审批状态", max_length=20, choices=APPROVAL_STATUS_CHOICES, default="DRAFT")
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_contract_adjustments",
        verbose_name="提交人",
    )
    submitted_at = models.DateTimeField("提交时间", null=True, blank=True)
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_contract_adjustments",
        verbose_name="审批人",
    )
    approver_name = models.CharField("审批人姓名", max_length=50, default="倪明珠")
    approved_at = models.DateTimeField("审批通过时间", null=True, blank=True)
    approval_comment = models.CharField("审批意见", max_length=500, blank=True)
    return_reason = models.CharField("退回原因", max_length=500, blank=True)
    approval_suggestion = models.TextField("审批辅助建议", blank=True)
    suggestion_generated_at = models.DateTimeField("建议生成时间", null=True, blank=True)

    source_system = models.CharField("来源系统", max_length=20, choices=SOURCE_SYSTEM_CHOICES)
    source_record_id = models.CharField("来源记录ID", max_length=100, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    created_by = models.CharField("创建人", max_length=50, blank=True, default="")
    updated_by = models.CharField("更新人", max_length=50, blank=True, default="")

    class Meta:
        verbose_name = "合同调整记录"
        verbose_name_plural = "合同调整记录"
        ordering = ["-adjustment_date", "-created_at"]
        indexes = [
            models.Index(fields=["contract"], name="idx_adj_contract"),
            models.Index(fields=["project"], name="idx_adj_project"),
            models.Index(fields=["approval_status"], name="idx_adj_status"),
            models.Index(fields=["adjustment_type"], name="idx_adj_type"),
            models.Index(fields=["adjustment_date"], name="idx_adj_date"),
            models.Index(fields=["source_system"], name="idx_adj_source"),
            models.Index(fields=["contract_ct_code_snapshot"], name="idx_adj_ct_snapshot"),
            models.Index(fields=["contract", "approval_status"], name="idx_adj_contract_status"),
            models.Index(fields=["contract", "adjustment_type"], name="idx_adj_contract_type"),
            models.Index(fields=["project", "approval_status"], name="idx_adj_project_status"),
            models.Index(fields=["contract_ct_code_snapshot", "approval_status"], name="idx_adj_ct_status"),
        ]

    def clean(self):
        expected_tax = (self.before_amount_tax or Decimal("0.00")) + (self.change_amount_tax or Decimal("0.00"))
        expected_notax = (self.before_amount_notax or Decimal("0.00")) + (self.change_amount_notax or Decimal("0.00"))
        if self.after_amount_tax != expected_tax:
            raise ValidationError("含税金额不满足：调整前 + 本次调整 = 调整后")
        if self.after_amount_notax != expected_notax:
            raise ValidationError("不含税金额不满足：调整前 + 本次调整 = 调整后")
        if self.after_amount_tax < 0 or self.after_amount_notax < 0:
            raise ValidationError("调整后金额不允许为负值")

    def save(self, *args, **kwargs):
        if not self.project_id:
            self.project = self.contract.project
        self.project_code_snapshot = self.contract.project_code_snapshot
        self.contract_ct_code_snapshot = self.contract.contract_ct_code
        self.contract_name_snapshot = self.contract.contract_name

        if self._state.adding and not self.before_counterparty_id:
            self.before_counterparty = self.contract.counterparty
            self.before_counterparty_name = self.contract.counterparty_name_snapshot
            self.before_amount_tax = self.contract.current_amount_tax
            self.before_amount_notax = self.contract.current_amount_notax
            self.before_tax_rate = self.contract.current_tax_rate

        if not self.after_tax_rate:
            self.after_tax_rate = self.before_tax_rate
        if not self.after_counterparty_id:
            self.after_counterparty = self.before_counterparty
        if self.after_counterparty_id:
            self.after_counterparty_name = self.after_counterparty.party_name

        self.after_amount_tax = (self.before_amount_tax or Decimal("0.00")) + (self.change_amount_tax or Decimal("0.00"))
        self.after_amount_notax = (self.before_amount_notax or Decimal("0.00")) + (self.change_amount_notax or Decimal("0.00"))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.contract_ct_code_snapshot} - {self.adjustment_no}"


class ContractAdjustmentActionLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    adjustment = models.ForeignKey(
        ContractAdjustment,
        on_delete=models.CASCADE,
        related_name="action_logs",
        verbose_name="调整记录",
    )
    action_type = models.CharField("动作类型", max_length=20, choices=ACTION_TYPE_CHOICES)
    action_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="contract_adjustment_actions",
        verbose_name="操作人",
    )
    action_at = models.DateTimeField("操作时间", auto_now_add=True)
    comment = models.CharField("动作说明", max_length=500, blank=True)
    from_status = models.CharField("动作前状态", max_length=20, blank=True)
    to_status = models.CharField("动作后状态", max_length=20, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "合同调整动作日志"
        verbose_name_plural = "合同调整动作日志"
        ordering = ["-action_at", "-id"]
        indexes = [
            models.Index(fields=["adjustment"], name="idx_adjlog_adjustment"),
            models.Index(fields=["action_type"], name="idx_adjlog_action"),
            models.Index(fields=["action_by"], name="idx_adjlog_user"),
            models.Index(fields=["action_at"], name="idx_adjlog_at"),
            models.Index(fields=["adjustment", "action_at"], name="idx_adjlog_adjustment_at"),
        ]

    def __str__(self):
        return f"{self.adjustment_id}-{self.action_type}"
