from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from openpyxl import Workbook, load_workbook
import re
import uuid

from .models import DictItem, ImportBatch, ImportError, ProjectMaster, ProjectMasterLog


PJ_CODE_REGEX = re.compile(r"^PJ\d{10}$")


class ImportRowError(Exception):
    def __init__(self, field_name, message):
        super().__init__(message)
        self.field_name = field_name

DICT_TYPES = {
    "ORG": "项目机构",
    "BUSINESS_UNIT": "业务板块",
    "DEPT": "项目承担部门",
    "PROJECT_TYPE": "项目类型",
    "ORG_MODE": "项目组织模式",
    "DATA_STATUS": "数据状态",
    "PROVINCE": "省",
    "CITY": "市",
}


def _get_dict_items(code):
    return DictItem.objects.filter(dict_type__code=code, is_active=True).order_by("sort_order", "code")


def _build_dict_map(code):
    return {item.code: item.name for item in _get_dict_items(code)}


def home(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if request.POST.get("remember"):
                request.session.set_expiry(60 * 60 * 24 * 30)
            else:
                request.session.set_expiry(0)
            return redirect("project_master_list")
        messages.error(request, "用户名或密码错误")
    return render(request, "home.html")


@login_required
def project_master_list(request):
    if request.method == "POST" and request.POST.get("form_type") == "create":
        pj_code = request.POST.get("project_code", "").strip()
        if not PJ_CODE_REGEX.match(pj_code):
            messages.error(request, "项目编号必须为PJ开头的12位编码")
            return redirect("project_master_list")

        created_by = request.POST.get("created_by", "").strip() or request.user.username
        parent_pj_code = request.POST.get("parent_pj_code", "").strip() or None
        is_execution_level = request.POST.get("is_execution_level") == "true"

        ProjectMaster.objects.create(
            project_code=pj_code,
            project_name=request.POST.get("project_name", "").strip(),
            org_name=request.POST.get("org_name", "").strip(),
            org_code=request.POST.get("org_code", "").strip(),
            parent_pj_code=parent_pj_code,
            province_code=request.POST.get("province_code", "").strip(),
            city_code=request.POST.get("city_code", "").strip(),
            business_unit=request.POST.get("business_unit", "").strip(),
            dept=request.POST.get("dept", "").strip(),
            project_type=request.POST.get("project_type", "").strip(),
            org_mode=request.POST.get("org_mode", "").strip(),
            data_status=request.POST.get("data_status", "").strip(),
            is_execution_level=is_execution_level,
            status=request.POST.get("status", "启用").strip() or "启用",
            created_by=created_by,
            updated_by=created_by,
            remark=request.POST.get("remark", "").strip(),
        )

        ProjectMasterLog.objects.create(
            project_code=pj_code,
            action="create",
            after_data={"project_code": pj_code, "project_name": request.POST.get("project_name")},
            operator=created_by,
            source="手工新增",
        )

        messages.success(request, "项目创建成功")
        return redirect("project_master_list")

    dict_data = {k: _get_dict_items(k) for k in DICT_TYPES}
    dict_maps = {k: _build_dict_map(k) for k in DICT_TYPES}

    projects = ProjectMaster.objects.filter(is_deleted=False)
    project_rows = []
    for p in projects:
        project_rows.append(
            {
                "project_code": p.project_code,
                "project_name": p.project_name,
                "org_name": p.org_name,
                "province_name": dict_maps["PROVINCE"].get(p.province_code, p.province_code),
                "city_name": dict_maps["CITY"].get(p.city_code, p.city_code),
                "business_unit_name": dict_maps["BUSINESS_UNIT"].get(p.business_unit, p.business_unit),
                "project_type_name": dict_maps["PROJECT_TYPE"].get(p.project_type, p.project_type),
                "created_at": p.created_at,
                "status": p.status,
            }
        )

    latest_batch = ImportBatch.objects.order_by("-imported_at").first()
    latest_errors = []
    if latest_batch:
        latest_errors = list(latest_batch.errors.all())

    return render(
        request,
        "project_master_list.html",
        {
            "projects": project_rows,
            "dicts": dict_data,
            "latest_errors": latest_errors,
        },
    )


@login_required
def project_master_edit(request, project_code):
    project = get_object_or_404(ProjectMaster, project_code=project_code, is_deleted=False)
    if request.method == "POST":
        before = {
            "project_name": project.project_name,
            "org_name": project.org_name,
            "org_code": project.org_code,
            "parent_pj_code": project.parent_pj_code,
            "province_code": project.province_code,
            "city_code": project.city_code,
            "business_unit": project.business_unit,
            "dept": project.dept,
            "project_type": project.project_type,
            "org_mode": project.org_mode,
            "data_status": project.data_status,
            "is_execution_level": project.is_execution_level,
            "status": project.status,
            "remark": project.remark,
        }

        project.project_name = request.POST.get("project_name", "").strip()
        project.org_name = request.POST.get("org_name", "").strip()
        project.org_code = request.POST.get("org_code", "").strip()
        project.parent_pj_code = request.POST.get("parent_pj_code", "").strip() or None
        project.province_code = request.POST.get("province_code", "").strip()
        project.city_code = request.POST.get("city_code", "").strip()
        project.business_unit = request.POST.get("business_unit", "").strip()
        project.dept = request.POST.get("dept", "").strip()
        project.project_type = request.POST.get("project_type", "").strip()
        project.org_mode = request.POST.get("org_mode", "").strip()
        project.data_status = request.POST.get("data_status", "").strip()
        project.is_execution_level = request.POST.get("is_execution_level") == "true"
        project.status = request.POST.get("status", "启用").strip() or "启用"
        project.remark = request.POST.get("remark", "").strip()
        project.updated_by = request.user.username
        project.data_version = project.data_version + 1
        project.save()

        ProjectMasterLog.objects.create(
            project_code=project.project_code,
            action="update",
            before_data=before,
            after_data={
                "project_name": project.project_name,
                "org_name": project.org_name,
                "org_code": project.org_code,
                "parent_pj_code": project.parent_pj_code,
                "province_code": project.province_code,
                "city_code": project.city_code,
                "business_unit": project.business_unit,
                "dept": project.dept,
                "project_type": project.project_type,
                "org_mode": project.org_mode,
                "data_status": project.data_status,
                "is_execution_level": project.is_execution_level,
                "status": project.status,
                "remark": project.remark,
            },
            operator=request.user.username,
            source="手工修改",
        )

        messages.success(request, "项目更新成功")
        return redirect("project_master_list")

    dict_data = {k: _get_dict_items(k) for k in DICT_TYPES}
    return render(
        request,
        "project_master_edit.html",
        {
            "project": project,
            "dicts": dict_data,
        },
    )


@login_required
def project_master_delete(request, project_code):
    if request.method != "POST":
        return redirect("project_master_list")

    project = get_object_or_404(ProjectMaster, project_code=project_code, is_deleted=False)
    before = {
        "project_name": project.project_name,
        "org_name": project.org_name,
        "org_code": project.org_code,
        "parent_pj_code": project.parent_pj_code,
        "province_code": project.province_code,
        "city_code": project.city_code,
        "business_unit": project.business_unit,
        "dept": project.dept,
        "project_type": project.project_type,
        "org_mode": project.org_mode,
        "data_status": project.data_status,
        "is_execution_level": project.is_execution_level,
        "status": project.status,
    }

    project.is_deleted = True
    project.updated_by = request.user.username
    project.data_version = project.data_version + 1
    project.save(update_fields=["is_deleted", "updated_by", "data_version", "updated_at"])

    ProjectMasterLog.objects.create(
        project_code=project.project_code,
        action="delete",
        before_data=before,
        after_data=None,
        operator=request.user.username,
        source="手工删除",
    )

    messages.success(request, "项目已删除")
    return redirect("project_master_list")


@login_required
def export_project_template(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "项目主数据模板"

    headers = [
        "项目主数据编码",
        "项目名称",
        "项目机构名称",
        "项目机构组织编码",
        "上级PJ编码",
        "所在省代码",
        "所在市代码",
        "业务板块",
        "项目承担部门",
        "项目类型",
        "项目组织模式",
        "主数据系统数据状态",
        "是否为执行层",
        "状态",
        "备注",
        "创建人",
    ]
    ws.append(headers)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=project_master_template.xlsx"
    wb.save(response)
    return response


@login_required
def import_project_master(request):
    if request.method != "POST":
        return redirect("project_master_list")

    upload = request.FILES.get("import_file")
    if not upload:
        messages.error(request, "请选择要导入的Excel文件")
        return redirect("project_master_list")

    batch_no = timezone.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    batch = ImportBatch.objects.create(
        batch_no=batch_no,
        source_file=upload.name,
        imported_by=getattr(request.user, "username", "system") or "system",
    )

    wb = load_workbook(upload)
    ws = wb.active

    total = 0
    success = 0
    fail = 0

    for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not any(row):
            continue
        total += 1
        try:
            (
                project_code,
                project_name,
                org_name,
                org_code,
                parent_pj_code,
                province_code,
                city_code,
                business_unit,
                dept,
                project_type,
                org_mode,
                data_status,
                is_execution_level,
                status,
                remark,
                created_by,
            ) = row

            project_code = str(project_code).strip()
            if not project_code:
                raise ImportRowError("项目主数据编码", "项目主数据编码不能为空")
            if not PJ_CODE_REGEX.match(project_code):
                raise ImportRowError("项目主数据编码", "项目编号必须为PJ开头的12位编码")

            if not project_name:
                raise ImportRowError("项目名称", "项目名称不能为空")
            if not org_name:
                raise ImportRowError("项目机构名称", "项目机构名称不能为空")
            if not org_code:
                raise ImportRowError("项目机构组织编码", "项目机构组织编码不能为空")
            if not province_code:
                raise ImportRowError("所在省代码", "所在省代码不能为空")
            if not city_code:
                raise ImportRowError("所在市代码", "所在市代码不能为空")
            if not business_unit:
                raise ImportRowError("业务板块", "业务板块不能为空")
            if not dept:
                raise ImportRowError("项目承担部门", "项目承担部门不能为空")
            if not project_type:
                raise ImportRowError("项目类型", "项目类型不能为空")
            if not org_mode:
                raise ImportRowError("项目组织模式", "项目组织模式不能为空")
            if not data_status:
                raise ImportRowError("主数据系统数据状态", "主数据系统数据状态不能为空")

            ProjectMaster.objects.create(
                project_code=project_code,
                project_name=str(project_name).strip(),
                org_name=str(org_name).strip(),
                org_code=str(org_code).strip(),
                parent_pj_code=str(parent_pj_code).strip() if parent_pj_code else None,
                province_code=str(province_code).strip(),
                city_code=str(city_code).strip(),
                business_unit=str(business_unit).strip(),
                dept=str(dept).strip(),
                project_type=str(project_type).strip(),
                org_mode=str(org_mode).strip(),
                data_status=str(data_status).strip(),
                is_execution_level=str(is_execution_level).strip() in ["是", "true", "True", "1"],
                status=str(status).strip() or "启用",
                created_by=str(created_by).strip() if created_by else "system",
                updated_by=str(created_by).strip() if created_by else "system",
                remark=str(remark).strip() if remark else "",
            )

            ProjectMasterLog.objects.create(
                project_code=project_code,
                action="import",
                after_data={"project_code": project_code, "project_name": project_name},
                operator=getattr(request.user, "username", "system") or "system",
                source=f"批量导入:{batch_no}",
            )

            success += 1
        except ImportRowError as exc:
            fail += 1
            ImportError.objects.create(
                batch=batch,
                row_number=idx,
                field_name=exc.field_name,
                error_message=str(exc),
                raw_data={"row": row},
            )
        except Exception as exc:
            fail += 1
            ImportError.objects.create(
                batch=batch,
                row_number=idx,
                field_name="",
                error_message=f"系统错误：{exc}",
                raw_data={"row": row},
            )

    batch.total_count = total
    batch.success_count = success
    batch.fail_count = fail
    batch.save(update_fields=["total_count", "success_count", "fail_count"])

    messages.success(request, f"导入完成：成功 {success} 条，失败 {fail} 条")
    return redirect("project_master_list")


@login_required
def user_list(request):
    if not request.user.is_staff:
        if request.method == "POST":
            messages.error(request, "无权限执行该操作")
            return redirect("user_list")
        users = User.objects.filter(id=request.user.id)
        return render(request, "user_list.html", {"users": users})

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            username = request.POST.get("username", "").strip()
            email = request.POST.get("email", "").strip()
            password = request.POST.get("password", "").strip()
            is_staff = request.POST.get("is_staff") == "true"
            if not username or not password:
                messages.error(request, "用户名和密码不能为空")
            elif User.objects.filter(username=username).exists():
                messages.error(request, "用户名已存在")
            else:
                user = User.objects.create(username=username, email=email, is_staff=is_staff, is_active=True)
                user.set_password(password)
                user.save(update_fields=["password"])
                messages.success(request, "用户创建成功")

        elif action == "toggle":
            user_id = request.POST.get("user_id")
            user = get_object_or_404(User, id=user_id)
            if user == request.user:
                messages.error(request, "不能禁用当前登录用户")
            else:
                user.is_active = not user.is_active
                user.save(update_fields=["is_active"])
                messages.success(request, "用户状态已更新")

        elif action == "reset":
            user_id = request.POST.get("user_id")
            new_password = request.POST.get("new_password", "").strip()
            user = get_object_or_404(User, id=user_id)
            if not new_password:
                messages.error(request, "新密码不能为空")
            else:
                user.set_password(new_password)
                user.save(update_fields=["password"])
                messages.success(request, "密码已重置")

        return redirect("user_list")

    users = User.objects.all().order_by("username")
    return render(request, "user_list.html", {"users": users})
