from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .models import ProjectMaster

def home(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('project_master_list')  # 后台数据库页面
        else:
            messages.error(request, "用户名或密码错误")
    return render(request, "home.html")

def project_master_list(request):
    if request.method == "POST":
        # 处理新增项目的表单提交
        pj_code = request.POST.get("pj_code")
        pj_name = request.POST.get("pj_name")
        org_name = request.POST.get("org_name")
        org_code = request.POST.get("org_code")
        parent_pj_code = request.POST.get("parent_pj_code")
        province_code = request.POST.get("province_code")
        city_code = request.POST.get("city_code")
        business_unit = request.POST.get("business_unit")
        dept = request.POST.get("dept")
        project_type = request.POST.get("project_type")
        org_mode = request.POST.get("org_mode")
        data_status = request.POST.get("data_status")
        exec_pj_code = request.POST.get("exec_pj_code")
        year = request.POST.get("year")
        created_by = request.POST.get("created_by")
        remark = request.POST.get("remark")
        
        # 创建新项目
        ProjectMaster.objects.create(
            pj_code=pj_code,
            pj_name=pj_name,
            org_name=org_name,
            org_code=org_code,
            parent_pj_code=parent_pj_code,
            province_code=province_code,
            city_code=city_code,
            business_unit=business_unit,
            dept=dept,
            project_type=project_type,
            org_mode=org_mode,
            data_status=data_status,
            exec_pj_code=exec_pj_code,
            year=year,
            created_by=created_by,
            updated_by=created_by,
            remark=remark
        )
        
        messages.success(request, "项目创建成功")
        return redirect('project_master_list')
    
    # 获取所有项目
    projects = ProjectMaster.objects.all()
    return render(request, "project_master_list.html", {"projects": projects})