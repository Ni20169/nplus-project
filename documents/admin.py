from django.contrib import admin
from .models import (
    ContractAdjustment,
    ContractAdjustmentActionLog,
    ContractMaster,
    Counterparty,
    DictItem,
    DictType,
    ImportBatch,
    ImportError,
    ProjectMaster,
    ProjectMasterLog,
    UserProfile,
)


@admin.register(DictType)
class DictTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "group", "is_active", "sort_order")
    search_fields = ("code", "name", "group")
    list_filter = ("is_active", "group")


@admin.register(DictItem)
class DictItemAdmin(admin.ModelAdmin):
    list_display = ("dict_type", "code", "name", "is_active", "sort_order")
    search_fields = ("code", "name", "value")
    list_filter = ("dict_type", "is_active")


@admin.register(ProjectMaster)
class ProjectMasterAdmin(admin.ModelAdmin):
    list_display = ("project_code", "project_name", "org_name", "project_year", "status")
    search_fields = ("project_code", "project_name", "org_name")
    list_filter = ("status", "project_year")


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_no", "source_file", "imported_by", "imported_at", "success_count", "fail_count")
    search_fields = ("batch_no", "source_file", "imported_by")


@admin.register(ImportError)
class ImportErrorAdmin(admin.ModelAdmin):
    list_display = ("batch", "row_number", "field_name", "error_message", "created_at")
    search_fields = ("batch__batch_no", "field_name", "error_message")


@admin.register(ProjectMasterLog)
class ProjectMasterLogAdmin(admin.ModelAdmin):
    list_display = ("project_code", "action", "operator", "created_at")
    search_fields = ("project_code", "operator")
    list_filter = ("action",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "department")
    search_fields = ("user__username", "department")


@admin.register(Counterparty)
class CounterpartyAdmin(admin.ModelAdmin):
    list_display = ("party_name", "party_type", "credit_code", "status", "updated_at")
    search_fields = ("party_name", "credit_code", "contact_name", "contact_phone")
    list_filter = ("party_type", "status")


@admin.register(ContractMaster)
class ContractMasterAdmin(admin.ModelAdmin):
    list_display = (
        "contract_ct_code",
        "contract_name",
        "project_code_snapshot",
        "contract_direction",
        "contract_category",
        "contract_status",
        "current_amount_tax",
    )
    search_fields = (
        "contract_ct_code",
        "contract_name",
        "project_code_snapshot",
        "counterparty_name_snapshot",
    )
    list_filter = ("source_system", "contract_direction", "contract_category", "contract_status", "contract_year")


@admin.register(ContractAdjustment)
class ContractAdjustmentAdmin(admin.ModelAdmin):
    list_display = (
        "contract_ct_code_snapshot",
        "adjustment_type",
        "adjustment_no",
        "approval_status",
        "change_amount_tax",
        "after_amount_tax",
        "adjustment_date",
    )
    search_fields = ("contract_ct_code_snapshot", "contract_name_snapshot", "adjustment_no")
    list_filter = ("adjustment_type", "approval_status", "source_system")


@admin.register(ContractAdjustmentActionLog)
class ContractAdjustmentActionLogAdmin(admin.ModelAdmin):
    list_display = ("adjustment", "action_type", "action_by", "action_at")
    search_fields = ("adjustment__contract_ct_code_snapshot", "action_by__username", "comment")
    list_filter = ("action_type",)
