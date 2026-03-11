from django.contrib import admin

from .models import ProjectMaster

@admin.register(ProjectMaster)
class ProjectMasterAdmin(admin.ModelAdmin):
    list_display = ('pj_code', 'pj_name', 'org_name', 'province_code', 'city_code', 'data_status')
