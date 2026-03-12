import uuid
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from .models import DictType, ImportBatch, ImportError, ProjectMaster, ProjectMasterLog, UserProfile


DICT_CODES = [
    "ORG",
    "BUSINESS_UNIT",
    "DEPT",
    "PROJECT_TYPE",
    "ORG_MODE",
    "DATA_STATUS",
    "PROVINCE",
    "CITY",
]


def _load_dicts():
    types = (
        DictType.objects.filter(code__in=DICT_CODES, is_active=True)
        .prefetch_related("items")
        .order_by("code")
    )
    dicts = {code: [] for code in DICT_CODES}
    for dt in types:
        dicts[dt.code] = list(
            dt.items.filter(is_active=True).order_by("sort_order", "code")
        )
    return dicts


def _dict_name_map(dicts):
    return {code: {item.code: item.name for item in items} for code, items in dicts.items()}


def home(request):
    if request.user.is_authenticated:
        return redirect("project_master_list")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        remember = request.POST.get("remember")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if not remember:
                request.session.set_expiry(0)
            return redirect("project_master_list")
        messages.error(request, "用户名或密码错误")

    return render(request, "home.html")


def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def project_master_list(request):
    dicts = _load_dicts()
    dict_map = _dict_name_map(dicts)

    if request.method == "POST" and request.POST.get("form_type") == "create":
        project_data = {
            "project_code": request.POST.get("project_code", "").strip(),
            "project_name": request.POST.get("project_name", "").strip(),
            "org_code": request.POST.get("org_code", "").strip(),
            "org_name": request.POST.get("org_name", "").strip(),
            "parent_pj_code": request.POST.get("parent_pj_code", "").strip() or None,
            "province_code": request.POST.get("province_code", "").strip(),
            "city_code": request.POST.get("city_code", "").strip(),
            "business_unit": request.POST.get("business_unit", "").strip(),
            "dept": request.POST.get("dept", "").strip(),
            "project_type": request.POST.get("project_type", "").strip(),
            "org_mode": request.POST.get("org_mode", "").strip(),
            "data_status": request.POST.get("data_status", "").strip(),
            "is_execution_level": request.POST.get("is_execution_level", "false")
            == "true",
            "status": request.POST.get("status", "启用").strip(),
            "created_by": request.POST.get("created_by", "").strip()
            or request.user.username,
            "updated_by": request.user.username,
            "remark": request.POST.get("remark", "").strip(),
        }

        if not project_data["city_code"]:
            project_data["city_code"] = project_data["province_code"]

        if project_data["project_code"] and len(project_data["project_code"]) >= 6:
            project_data["project_year"] = project_data["project_code"][2:6]
        else:
            project_data["project_year"] = ""

        if not project_data["org_name"] and project_data["org_code"]:
            project_data["org_name"] = dict_map.get("ORG", {}).get(
                project_data["org_code"], ""
            )

        try:
            with transaction.atomic():
                project = ProjectMaster(**project_data)
                project.full_clean()
                project.save()
                ProjectMasterLog.objects.create(
                    project_code=project.project_code,
                    action="create",
                    after_data=project_data,
                    operator=request.user.username,
                    source="web",
                )
            messages.success(request, "项目已新增")
            return redirect("project_master_list")
        except ValidationError as exc:
            messages.error(request, f"保存失败：{exc}")
        except Exception as exc:
            messages.error(request, f"保存失败：{exc}")

    show_update_panel = False

    if request.method == "POST" and request.POST.get("form_type") == "update":
        target_code = request.POST.get("update_project_code", "").strip()
        project = ProjectMaster.objects.filter(project_code=target_code, is_deleted=False).first()
        if not project:
            messages.error(request, "未找到需要更新的项目")
            return redirect("project_master_list")

        before = {
            "project_name": project.project_name,
            "org_name": project.org_name,
            "org_code": project.org_code,
            "parent_pj_code": project.parent_pj_code,
            "province_code": project.province_code,
            "business_unit": project.business_unit,
            "dept": project.dept,
            "project_type": project.project_type,
            "org_mode": project.org_mode,
            "data_status": project.data_status,
            "is_execution_level": project.is_execution_level,
            "status": project.status,
            "remark": project.remark,
        }

        project.project_name = request.POST.get("project_name", project.project_name).strip()
        project.org_code = request.POST.get("org_code", project.org_code).strip()
        project.org_name = request.POST.get("org_name", project.org_name).strip()
        project.parent_pj_code = request.POST.get("parent_pj_code", "").strip() or None
        project.province_code = request.POST.get("province_code", project.province_code).strip()
        if not project.city_code:
            project.city_code = project.province_code
        project.business_unit = request.POST.get("business_unit", project.business_unit).strip()
        project.dept = request.POST.get("dept", project.dept).strip()
        project.project_type = request.POST.get("project_type", project.project_type).strip()
        project.org_mode = request.POST.get("org_mode", project.org_mode).strip()
        project.data_status = request.POST.get("data_status", project.data_status).strip()
        project.is_execution_level = request.POST.get("is_execution_level", "false") == "true"
        project.status = request.POST.get("status", project.status).strip()
        project.remark = request.POST.get("remark", "").strip()
        project.updated_by = request.user.username
        change_note = request.POST.get("update_note", "").strip()

        if not project.org_name and project.org_code:
            project.org_name = dict_map.get("ORG", {}).get(project.org_code, project.org_name)

        try:
            with transaction.atomic():
                project.full_clean()
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
                        "business_unit": project.business_unit,
                        "dept": project.dept,
                        "project_type": project.project_type,
                        "org_mode": project.org_mode,
                        "data_status": project.data_status,
                        "is_execution_level": project.is_execution_level,
                        "status": project.status,
                        "remark": project.remark,
                    },
                    change_note=change_note,
                    operator=request.user.username,
                    source="update-panel",
                )
            messages.success(request, "更新成功")
        except ValidationError as exc:
            messages.error(request, f"更新失败：{exc}")
        except Exception as exc:
            messages.error(request, f"更新失败：{exc}")
        show_update_panel = True

    qs = ProjectMaster.objects.filter(is_deleted=False)
    search = {
        "project_code": request.GET.get("project_code", "").strip(),
        "project_name": request.GET.get("project_name", "").strip(),
        "org_name": request.GET.get("org_name", "").strip(),
        "org_code": request.GET.get("org_code", "").strip(),
        "parent_pj_code": request.GET.get("parent_pj_code", "").strip(),
        "province_code": request.GET.get("province_code", "").strip(),
        "business_unit": request.GET.get("business_unit", "").strip(),
        "dept": request.GET.get("dept", "").strip(),
        "project_type": request.GET.get("project_type", "").strip(),
        "org_mode": request.GET.get("org_mode", "").strip(),
        "data_status": request.GET.get("data_status", "").strip(),
        "is_execution_level": request.GET.get("is_execution_level", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "project_year": request.GET.get("project_year", "").strip(),
        "created_by": request.GET.get("created_by", "").strip(),
        "remark": request.GET.get("remark", "").strip(),
    }

    if search["project_code"]:
        qs = qs.filter(project_code__icontains=search["project_code"])
    if search["project_name"]:
        qs = qs.filter(project_name__icontains=search["project_name"])
    if search["org_name"]:
        qs = qs.filter(org_name__icontains=search["org_name"])
    if search["org_code"]:
        qs = qs.filter(org_code__icontains=search["org_code"])
    if search["parent_pj_code"]:
        qs = qs.filter(parent_pj_code__icontains=search["parent_pj_code"])
    if search["province_code"]:
        qs = qs.filter(province_code=search["province_code"])
    if search["business_unit"]:
        qs = qs.filter(business_unit=search["business_unit"])
    if search["dept"]:
        qs = qs.filter(dept=search["dept"])
    if search["project_type"]:
        qs = qs.filter(project_type=search["project_type"])
    if search["org_mode"]:
        qs = qs.filter(org_mode=search["org_mode"])
    if search["data_status"]:
        qs = qs.filter(data_status=search["data_status"])
    if search["is_execution_level"] == "true":
        qs = qs.filter(is_execution_level=True)
    if search["is_execution_level"] == "false":
        qs = qs.filter(is_execution_level=False)
    if search["status"]:
        qs = qs.filter(status=search["status"])
    if search["project_year"]:
        qs = qs.filter(project_year__icontains=search["project_year"])
    if search["created_by"]:
        qs = qs.filter(created_by__icontains=search["created_by"])
    if search["remark"]:
        qs = qs.filter(remark__icontains=search["remark"])

    projects = list(qs.order_by("-created_at"))
    name_map = _dict_name_map(dicts)
    for project in projects:
        project.province_name = name_map.get("PROVINCE", {}).get(
            project.province_code, project.province_code
        )
        project.city_name = name_map.get("CITY", {}).get(project.city_code, project.city_code)
        project.business_unit_name = name_map.get("BUSINESS_UNIT", {}).get(
            project.business_unit, project.business_unit
        )
        project.dept_name = name_map.get("DEPT", {}).get(project.dept, project.dept)
        project.org_mode_name = name_map.get("ORG_MODE", {}).get(project.org_mode, project.org_mode)
        project.data_status_name = name_map.get("DATA_STATUS", {}).get(project.data_status, project.data_status)
        project.project_type_name = name_map.get("PROJECT_TYPE", {}).get(
            project.project_type, project.project_type
        )

    latest_errors = []
    latest_batch = ImportBatch.objects.order_by("-imported_at").first()
    if latest_batch:
        latest_errors = list(latest_batch.errors.all())

    recent_updates = list(
        ProjectMasterLog.objects.filter(action="update").order_by("-created_at")[:10]
    )
    field_labels = {
        "project_name": "项目名称",
        "org_name": "项目机构",
        "org_code": "项目机构组织编码",
        "parent_pj_code": "上级PJ编码",
        "province_code": "所在省",
        "business_unit": "业务板块",
        "dept": "项目承担部门",
        "project_type": "项目类型",
        "org_mode": "项目组织模式",
        "data_status": "主数据系统数据状态",
        "is_execution_level": "是否为执行层",
        "status": "状态",
        "remark": "备注",
    }
    for log in recent_updates:
        before = log.before_data or {}
        after = log.after_data or {}
        changed = []
        before_lines = []
        after_lines = []
        for key, label in field_labels.items():
            before_val = before.get(key)
            after_val = after.get(key)
            if before_val != after_val:
                changed.append(label)
                if key == "is_execution_level":
                    before_val = "是" if before_val else "否"
                    after_val = "是" if after_val else "否"
                before_lines.append(f"{label}：{before_val}")
                after_lines.append(f"{label}：{after_val}")
        log.changed_fields = "、".join(changed) if changed else "无"
        log.before_summary = "\n".join(before_lines) if before_lines else "无"
        log.after_summary = "\n".join(after_lines) if after_lines else "无"

    update_code = request.GET.get("update_code", "").strip()
    update_name = request.GET.get("update_name", "").strip()
    update_candidates = ProjectMaster.objects.filter(is_deleted=False)
    if update_code:
        update_candidates = update_candidates.filter(project_code__icontains=update_code)
    if update_name:
        update_candidates = update_candidates.filter(project_name__icontains=update_name)
    update_candidates = list(update_candidates.order_by("-created_at")[:20])

    update_target_code = request.GET.get("update_target", "").strip()
    update_target = None
    if update_target_code:
        update_target = ProjectMaster.objects.filter(
            project_code=update_target_code, is_deleted=False
        ).first()
        show_update_panel = True
    if update_code or update_name:
        show_update_panel = True

    return render(
        request,
        "project_master_list.html",
        {
            "projects": projects,
            "dicts": dicts,
            "latest_errors": latest_errors,
            "search": search,
            "recent_updates": recent_updates,
            "update_candidates": update_candidates,
            "update_target": update_target,
            "update_code": update_code,
            "update_name": update_name,
            "show_update_panel": show_update_panel,
            "update_now": timezone.localtime().strftime("%Y-%m-%d %H:%M"),
        },
    )


@login_required
def export_project_template(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "项目主数据模板"
    headers = [
        "项目主数据编码",
        "项目名称",
        "项目机构组织编码",
        "项目机构名称",
        "上级PJ编码",
        "所在省",
        "业务板块",
        "项目承担部门",
        "项目类型",
        "项目组织模式",
        "主数据系统数据状态",
        "是否为执行层",
        "状态",
        "备注",
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

    file = request.FILES.get("import_file")
    if not file:
        messages.error(request, "请选择要导入的文件")
        return redirect("project_master_list")

    dicts = _load_dicts()
    name_map = _dict_name_map(dicts)
    batch = ImportBatch.objects.create(
        batch_no=uuid.uuid4().hex[:12],
        source_file=file.name,
        imported_by=request.user.username,
    )

    wb = load_workbook(file, data_only=True)
    ws = wb.active
    headers = [str(cell.value).strip() if cell.value else "" for cell in ws[1]]
    header_map = {
        "项目主数据编码": "project_code",
        "项目名称": "project_name",
        "项目机构组织编码": "org_code",
        "项目机构名称": "org_name",
        "上级PJ编码": "parent_pj_code",
        "所在省": "province_code",
        "所在市": "city_code",
        "业务板块": "business_unit",
        "项目承担部门": "dept",
        "项目类型": "project_type",
        "项目组织模式": "org_mode",
        "主数据系统数据状态": "data_status",
        "是否为执行层": "is_execution_level",
        "状态": "status",
        "备注": "remark",
    }

    field_idx = {}
    for idx, header in enumerate(headers):
        field = header_map.get(header)
        if field:
            field_idx[field] = idx

    required_fields = [
        "project_code",
        "project_name",
        "org_code",
        "province_code",
        "business_unit",
        "dept",
        "project_type",
        "org_mode",
        "data_status",
        "is_execution_level",
        "status",
    ]

    success = 0
    failure = 0
    total = 0

    for row_index, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        total += 1
        row_data = {}
        for field, idx in field_idx.items():
            row_data[field] = (row[idx] if idx < len(row) else "") or ""

        missing = [field for field in required_fields if not row_data.get(field)]
        if missing:
            ImportError.objects.create(
                batch=batch,
                row_number=row_index,
                field_name=",".join(missing),
                error_message="必填字段缺失",
                raw_data=row_data,
            )
            failure += 1
            continue

        row_data["org_name"] = row_data.get("org_name") or name_map.get("ORG", {}).get(
            str(row_data.get("org_code")).strip(), ""
        )
        row_data["city_code"] = row_data.get("city_code") or row_data.get("province_code")
        row_data["parent_pj_code"] = row_data.get("parent_pj_code") or None
        row_data["is_execution_level"] = str(row_data.get("is_execution_level")).strip() in [
            "true",
            "True",
            "是",
            "1",
        ]
        if row_data.get("project_code") and len(str(row_data.get("project_code"))) >= 6:
            row_data["project_year"] = str(row_data.get("project_code"))[2:6]
        else:
            row_data["project_year"] = ""
        row_data["created_by"] = request.user.username
        row_data["updated_by"] = request.user.username

        try:
            with transaction.atomic():
                project = ProjectMaster(**row_data)
                project.full_clean()
                project.save()
                ProjectMasterLog.objects.create(
                    project_code=project.project_code,
                    action="import",
                    after_data=row_data,
                    operator=request.user.username,
                    source="import",
                )
            success += 1
        except Exception as exc:
            ImportError.objects.create(
                batch=batch,
                row_number=row_index,
                field_name="",
                error_message=str(exc),
                raw_data=row_data,
            )
            failure += 1

    batch.total_count = total
    batch.success_count = success
    batch.fail_count = failure
    batch.save(update_fields=["total_count", "success_count", "fail_count"])

    if failure:
        messages.warning(request, f"导入完成，成功 {success} 条，失败 {failure} 条。")
    else:
        messages.success(request, f"导入完成，成功 {success} 条。")
    return redirect("project_master_list")


@login_required
def project_master_edit(request, project_code):
    dicts = _load_dicts()
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
        project.org_code = request.POST.get("org_code", "").strip()
        project.org_name = request.POST.get("org_name", "").strip()
        project.parent_pj_code = request.POST.get("parent_pj_code", "").strip() or None
        project.province_code = request.POST.get("province_code", "").strip()
        project.city_code = request.POST.get("city_code", "").strip() or project.province_code
        project.business_unit = request.POST.get("business_unit", "").strip()
        project.dept = request.POST.get("dept", "").strip()
        project.project_type = request.POST.get("project_type", "").strip()
        project.org_mode = request.POST.get("org_mode", "").strip()
        project.data_status = request.POST.get("data_status", "").strip()
        project.is_execution_level = request.POST.get("is_execution_level", "false") == "true"
        project.status = request.POST.get("status", "").strip()
        project.remark = request.POST.get("remark", "").strip()
        project.updated_by = request.user.username

        if not project.org_name and project.org_code:
            name_map = _dict_name_map(dicts)
            project.org_name = name_map.get("ORG", {}).get(project.org_code, "")

        try:
            with transaction.atomic():
                project.full_clean()
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
                    source="web",
                )
            messages.success(request, "项目已更新")
            return redirect("project_master_list")
        except ValidationError as exc:
            messages.error(request, f"保存失败：{exc}")
        except Exception as exc:
            messages.error(request, f"保存失败：{exc}")

    latest_update = (
        ProjectMasterLog.objects.filter(project_code=project.project_code, action="update")
        .order_by("-created_at")
        .first()
    )

    return render(
        request,
        "project_master_edit.html",
        {
            "project": project,
            "dicts": dicts,
            "latest_update": latest_update,
        },
    )


@login_required
def project_master_delete(request, project_code):
    project = get_object_or_404(ProjectMaster, project_code=project_code, is_deleted=False)
    if request.method == "POST":
        project.is_deleted = True
        project.updated_by = request.user.username
        project.save(update_fields=["is_deleted", "updated_by"])
        ProjectMasterLog.objects.create(
            project_code=project.project_code,
            action="delete",
            before_data={"project_code": project.project_code},
            operator=request.user.username,
            source="web",
        )
        messages.success(request, "项目已删除")
    return redirect("project_master_list")


@login_required
def user_list(request):
    if request.user.is_staff:
        users = User.objects.all().order_by("-date_joined")
    else:
        users = User.objects.filter(id=request.user.id)

    for user in users:
        UserProfile.objects.get_or_create(user=user)

    if request.method == "POST" and request.user.is_staff:
        action = request.POST.get("action")
        if action == "create":
            username = request.POST.get("username", "").strip()
            email = request.POST.get("email", "").strip()
            password = request.POST.get("password", "").strip()
            department = request.POST.get("department", "").strip()
            is_staff = request.POST.get("is_staff") == "true"
            if username and password:
                new_user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    is_staff=is_staff,
                )
                profile, _ = UserProfile.objects.get_or_create(user=new_user)
                profile.department = department
                profile.save(update_fields=["department"])
                messages.success(request, "用户已创建")
            else:
                messages.error(request, "用户名和密码不能为空")
        elif action == "toggle":
            user_id = request.POST.get("user_id")
            target = get_object_or_404(User, id=user_id)
            target.is_active = not target.is_active
            target.save(update_fields=["is_active"])
            messages.success(request, "用户状态已更新")
        elif action == "reset":
            user_id = request.POST.get("user_id")
            new_password = request.POST.get("new_password", "").strip()
            target = get_object_or_404(User, id=user_id)
            if new_password:
                target.set_password(new_password)
                target.save(update_fields=["password"])
                messages.success(request, "密码已重置")
            else:
                messages.error(request, "请输入新密码")
        return redirect("user_list")

    return render(request, "user_list.html", {"users": users})
