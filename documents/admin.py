from django.contrib import admin
from .models import DictType, DictItem, ProjectMaster, ImportBatch, ImportError, ProjectMasterLog, UserProfile


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
    list_display = ("project_code", "project_name", "org_name", "project_year", "data_status")
    search_fields = ("project_code", "project_name", "org_name")
    list_filter = ("data_status", "project_year")


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
