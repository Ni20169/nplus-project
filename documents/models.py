from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


PJ_CODE_REGEX = r"^PJ\d{10}$"


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
