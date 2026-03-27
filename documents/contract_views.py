import re
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from .models import (
    ADJUSTMENT_TYPE_CHOICES,
    APPROVAL_STATUS_CHOICES,
    CONTRACT_CATEGORY_CHOICES,
    CONTRACT_DIRECTION_CHOICES,
    CONTRACT_STATUS_CHOICES,
    DictType,
    PARTY_TYPE_CHOICES,
    SOURCE_SYSTEM_CHOICES,
    ContractAdjustment,
    ContractAdjustmentActionLog,
    ContractMaster,
    Counterparty,
    ProjectMaster,
)

CT_CODE_PATTERN = re.compile(r"^CT\d{12}$")


def _get_permissions(user):
    from .views import _get_user_permissions
    return _get_user_permissions(user)


def _get_dept_name_map():
    dept_type = DictType.objects.filter(code="DEPT", is_active=True).prefetch_related("items").first()
    if not dept_type:
        return {}
    return {
        item.code: item.name
        for item in dept_type.items.all()
        if item.is_active
    }


def _to_decimal(value, default="0"):
    text = str(value if value is not None else "").strip()
    if text == "":
        text = default
    return Decimal(text)


@login_required
def export_counterparty_template(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "往来单位导入模板"
    ws.append([
        "单位名称",
        "单位类型",
        "统一社会信用代码",
        "联系人",
        "联系电话",
        "状态",
        "备注",
    ])

    ws_ref = wb.create_sheet(title="字典参考")
    ws_ref.append(["字段", "可选值", "说明"])
    ws_ref.append(["单位类型", "OWNER", "业主"])
    ws_ref.append(["单位类型", "SUPPLIER", "供应商"])
    ws_ref.append(["单位类型", "SUBCONTRACTOR", "分包商"])
    ws_ref.append(["单位类型", "SUPPLY_SUB", "供应&分包商"])
    ws_ref.append(["单位类型", "OTHER_VENDOR", "其他外委单位"])
    ws_ref.append(["状态", "ACTIVE", "启用"])
    ws_ref.append(["状态", "INACTIVE", "停用"])

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 26
    ws.column_dimensions["D"].width = 16
    ws.column_dimensions["E"].width = 16
    ws.column_dimensions["F"].width = 12
    ws.column_dimensions["G"].width = 30
    ws_ref.column_dimensions["A"].width = 16
    ws_ref.column_dimensions["B"].width = 20
    ws_ref.column_dimensions["C"].width = 28

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=counterparty_import_template.xlsx"
    wb.save(response)
    return response


@login_required
def export_contract_template(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "合同台账导入模板"
    ws.append([
        "项目主数据编码",
        "合同CT码",
        "合同名称",
        "统一社会信用代码",
        "合同编号",
        "来源系统",
        "合同方向",
        "合同分类",
        "合同年份",
        "原始含税金额",
        "原始不含税金额",
        "原始税率",
        "当前含税金额",
        "当前不含税金额",
        "当前税率",
        "合同状态",
        "备注",
    ])

    ws_ref = wb.create_sheet(title="字典参考")
    ws_ref.append(["字段", "可选值", "说明"])
    for value, label in SOURCE_SYSTEM_CHOICES:
        ws_ref.append(["来源系统", value, label])
    for value, label in CONTRACT_DIRECTION_CHOICES:
        ws_ref.append(["合同方向", value, label])
    for value, label in CONTRACT_CATEGORY_CHOICES:
        ws_ref.append(["合同分类", value, label])
    for value, label in CONTRACT_STATUS_CHOICES:
        ws_ref.append(["合同状态", value, label])

    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 30
    ws.column_dimensions["D"].width = 24
    ws.column_dimensions["E"].width = 20
    ws.column_dimensions["F"].width = 16
    ws.column_dimensions["G"].width = 16
    ws.column_dimensions["H"].width = 16
    ws.column_dimensions["I"].width = 12
    ws.column_dimensions["J"].width = 16
    ws.column_dimensions["K"].width = 16
    ws.column_dimensions["L"].width = 12
    ws.column_dimensions["M"].width = 16
    ws.column_dimensions["N"].width = 16
    ws.column_dimensions["O"].width = 12
    ws.column_dimensions["P"].width = 14
    ws.column_dimensions["Q"].width = 30
    ws_ref.column_dimensions["A"].width = 16
    ws_ref.column_dimensions["B"].width = 20
    ws_ref.column_dimensions["C"].width = 28

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=contract_import_template.xlsx"
    wb.save(response)
    return response


def _log_adjustment_action(adjustment, action_type, user, comment="", from_status="", to_status=""):
    ContractAdjustmentActionLog.objects.create(
        adjustment=adjustment,
        action_type=action_type,
        action_by=user,
        comment=comment,
        from_status=from_status,
        to_status=to_status,
    )


def _apply_adjustment_to_contract(adjustment):
    contract = adjustment.contract
    contract.current_amount_tax = adjustment.after_amount_tax
    contract.current_amount_notax = adjustment.after_amount_notax
    contract.current_tax_rate = adjustment.after_tax_rate
    if adjustment.after_counterparty_id:
        contract.counterparty = adjustment.after_counterparty
        contract.counterparty_name_snapshot = adjustment.after_counterparty_name
    contract.approved_adjustment_count = contract.approved_adjustment_count + 1
    contract.last_adjustment_date = adjustment.adjustment_date
    contract.save()


# ---------------------------------------------------------------------------
# 往来单位管理
# ---------------------------------------------------------------------------

@login_required
def contract_counterparty_view(request):
    permissions = _get_permissions(request.user)

    if request.method == "POST" and request.POST.get("form_type") == "create_counterparty":
        credit_code = request.POST.get("credit_code", "").strip().upper()
        if len(credit_code) != 18:
            messages.error(request, "统一社会信用代码必须为18位")
            return redirect("contract_counterparty_list")
        if Counterparty.objects.filter(credit_code=credit_code).exists():
            messages.error(request, "统一社会信用代码已存在，请确保唯一")
            return redirect("contract_counterparty_list")
        try:
            with transaction.atomic():
                Counterparty.objects.create(
                    party_name=request.POST.get("party_name", "").strip(),
                    party_type=request.POST.get("party_type", "").strip(),
                    credit_code=credit_code,
                    contact_name=request.POST.get("contact_name", "").strip(),
                    contact_phone=request.POST.get("contact_phone", "").strip(),
                    status=request.POST.get("status", "ACTIVE").strip() or "ACTIVE",
                    remark=request.POST.get("remark", "").strip(),
                    created_by=request.user.username,
                    updated_by=request.user.username,
                )
            messages.success(request, "往来单位已新增")
        except Exception as exc:
            messages.error(request, f"往来单位保存失败：{exc}")
        return redirect("contract_counterparty_list")

    filters = {
        "party_name": request.GET.get("party_name", "").strip(),
        "party_type": request.GET.get("party_type", "").strip(),
        "credit_code": request.GET.get("credit_code", "").strip(),
        "status": request.GET.get("status", "").strip(),
    }
    qs = Counterparty.objects.all()
    if filters["party_name"]:
        qs = qs.filter(party_name__icontains=filters["party_name"])
    if filters["party_type"]:
        qs = qs.filter(party_type=filters["party_type"])
    if filters["credit_code"]:
        qs = qs.filter(credit_code__icontains=filters["credit_code"])
    if filters["status"]:
        qs = qs.filter(status=filters["status"])

    context = {
        "counterparties": list(qs.order_by("party_name")[:500]),
        "filters": filters,
        "permissions": permissions,
        "party_type_choices": PARTY_TYPE_CHOICES,
        "active_menu": "contract_counterparty",
        "total_count": qs.count(),
    }
    return render(request, "contract_counterparty.html", context)


# ---------------------------------------------------------------------------
# 合同台账管理
# ---------------------------------------------------------------------------

@login_required
def contract_list_view(request):
    permissions = _get_permissions(request.user)
    dept_name_map = _get_dept_name_map()

    if request.method == "POST" and request.POST.get("form_type") == "create_contract":
        project_id = request.POST.get("project_id", "").strip()
        counterparty_id = request.POST.get("counterparty_id", "").strip()
        ct_code = request.POST.get("contract_ct_code", "").strip().upper()
        if not CT_CODE_PATTERN.fullmatch(ct_code):
            messages.error(request, "CT码格式错误，必须为CT+12位数字")
            return redirect("contract_list")
        try:
            project = ProjectMaster.objects.get(id=project_id, is_deleted=False)
            counterparty = Counterparty.objects.get(id=counterparty_id)
            with transaction.atomic():
                contract = ContractMaster(
                    project=project,
                    counterparty=counterparty,
                    contract_ct_code=ct_code,
                    contract_name=request.POST.get("contract_name", "").strip(),
                    contract_no=request.POST.get("contract_no", "").strip(),
                    source_system=request.POST.get("source_system", "").strip(),
                    source_record_id=request.POST.get("source_record_id", "").strip(),
                    source_contract_no=request.POST.get("source_contract_no", "").strip(),
                    contract_direction=request.POST.get("contract_direction", "").strip(),
                    contract_category=request.POST.get("contract_category", "").strip(),
                    undertaking_dept_code="",
                    undertaking_dept_name=dept_name_map.get(project.dept, project.dept or ""),
                    contract_year=request.POST.get("contract_year", "").strip(),
                    sign_date=request.POST.get("sign_date") or None,
                    effective_date=request.POST.get("effective_date") or None,
                    close_date=request.POST.get("close_date") or None,
                    original_amount_tax=_to_decimal(request.POST.get("original_amount_tax", "0")),
                    original_amount_notax=_to_decimal(request.POST.get("original_amount_notax", "0")),
                    original_tax_rate=_to_decimal(request.POST.get("original_tax_rate"), default="0") if request.POST.get("original_tax_rate", "").strip() else None,
                    current_amount_tax=_to_decimal(request.POST.get("current_amount_tax", "0")),
                    current_amount_notax=_to_decimal(request.POST.get("current_amount_notax", "0")),
                    current_tax_rate=_to_decimal(request.POST.get("current_tax_rate"), default="0") if request.POST.get("current_tax_rate", "").strip() else None,
                    contract_status=request.POST.get("contract_status", "SIGNED").strip() or "SIGNED",
                    remark=request.POST.get("remark", "").strip(),
                    created_by=request.user.username,
                    updated_by=request.user.username,
                )
                if contract.current_amount_tax == Decimal("0") and contract.current_amount_notax == Decimal("0"):
                    contract.current_amount_tax = contract.original_amount_tax
                    contract.current_amount_notax = contract.original_amount_notax
                    if not contract.current_tax_rate:
                        contract.current_tax_rate = contract.original_tax_rate
                contract.full_clean()
                contract.save()
            messages.success(request, "合同已新增")
        except Exception as exc:
            messages.error(request, f"合同保存失败：{exc}")
        return redirect("contract_list")

    filters = {
        "project_code": request.GET.get("project_code", "").strip(),
        "contract_ct_code": request.GET.get("contract_ct_code", "").strip(),
        "contract_name": request.GET.get("contract_name", "").strip(),
        "source_system": request.GET.get("source_system", "").strip(),
        "contract_direction": request.GET.get("contract_direction", "").strip(),
        "contract_category": request.GET.get("contract_category", "").strip(),
        "contract_status": request.GET.get("contract_status", "").strip(),
        "undertaking_dept": request.GET.get("undertaking_dept", "").strip(),
        "contract_year": request.GET.get("contract_year", "").strip(),
        "counterparty_name": request.GET.get("counterparty_name", "").strip(),
    }
    qs = ContractMaster.objects.filter(is_deleted=False).select_related("project", "counterparty")
    if filters["project_code"]:
        qs = qs.filter(project_code_snapshot__icontains=filters["project_code"])
    if filters["contract_ct_code"]:
        qs = qs.filter(contract_ct_code__icontains=filters["contract_ct_code"])
    if filters["contract_name"]:
        qs = qs.filter(contract_name__icontains=filters["contract_name"])
    if filters["source_system"]:
        qs = qs.filter(source_system=filters["source_system"])
    if filters["contract_direction"]:
        qs = qs.filter(contract_direction=filters["contract_direction"])
    if filters["contract_category"]:
        qs = qs.filter(contract_category=filters["contract_category"])
    if filters["contract_status"]:
        qs = qs.filter(contract_status=filters["contract_status"])
    if filters["undertaking_dept"]:
        qs = qs.filter(undertaking_dept_name__icontains=filters["undertaking_dept"])
    if filters["contract_year"]:
        qs = qs.filter(contract_year__icontains=filters["contract_year"])
    if filters["counterparty_name"]:
        qs = qs.filter(counterparty_name_snapshot__icontains=filters["counterparty_name"])

    projects = list(ProjectMaster.objects.filter(is_deleted=False).order_by("-project_code"))
    for project in projects:
        project.dept_name = dept_name_map.get(project.dept, project.dept or "")

    context = {
        "contracts": list(qs.order_by("-created_at")[:300]),
        "projects": projects,
        "counterparties": Counterparty.objects.filter(status="ACTIVE").order_by("party_name"),
        "filters": filters,
        "permissions": permissions,
        "source_system_choices": SOURCE_SYSTEM_CHOICES,
        "contract_direction_choices": CONTRACT_DIRECTION_CHOICES,
        "contract_category_choices": CONTRACT_CATEGORY_CHOICES,
        "contract_status_choices": CONTRACT_STATUS_CHOICES,
        "active_menu": "contract_list",
        "total_count": qs.count(),
    }
    return render(request, "contract_list.html", context)


# ---------------------------------------------------------------------------
# 合同调整管理
# ---------------------------------------------------------------------------

@login_required
def contract_adjustment_view(request):
    permissions = _get_permissions(request.user)

    if request.method == "POST":
        form_type = request.POST.get("form_type", "").strip()

        if form_type == "create_adjustment":
            contract_id = request.POST.get("contract_id", "").strip()
            try:
                contract = ContractMaster.objects.get(id=contract_id, is_deleted=False)
                with transaction.atomic():
                    adjustment = ContractAdjustment(
                        contract=contract,
                        project=contract.project,
                        adjustment_type=request.POST.get("adjustment_type", "").strip(),
                        adjustment_no=request.POST.get("adjustment_no", "").strip(),
                        adjustment_date=request.POST.get("adjustment_date"),
                        effective_date=request.POST.get("effective_date") or None,
                        change_amount_tax=_to_decimal(request.POST.get("change_amount_tax", "0")),
                        change_amount_notax=_to_decimal(request.POST.get("change_amount_notax", "0")),
                        after_tax_rate=_to_decimal(request.POST.get("after_tax_rate"), default="0") if request.POST.get("after_tax_rate", "").strip() else None,
                        after_counterparty_id=request.POST.get("after_counterparty_id") or None,
                        remark=request.POST.get("remark", "").strip(),
                        approval_status=request.POST.get("approval_status", "DRAFT").strip() or "DRAFT",
                        submitted_by=request.user,
                        submitted_at=timezone.now(),
                        approver_name="\u502a\u660e\u73e0",
                        source_system=request.POST.get("source_system", contract.source_system).strip() or contract.source_system,
                        source_record_id=request.POST.get("source_record_id", "").strip(),
                        created_by=request.user.username,
                        updated_by=request.user.username,
                    )
                    adjustment.save()
                    _log_adjustment_action(
                        adjustment, "EDIT", request.user,
                        comment="\u521b\u5efa\u8c03\u6574\u8bb0\u5f55", from_status="", to_status=adjustment.approval_status,
                    )
                    if adjustment.approval_status == "APPROVED":
                        _apply_adjustment_to_contract(adjustment)
                        _log_adjustment_action(
                            adjustment, "APPROVE", request.user,
                            comment="\u5f55\u5165\u5373\u901a\u8fc7\u5e76\u540c\u6b65\u4e3b\u8868",
                            from_status="APPROVED", to_status="APPROVED",
                        )
                messages.success(request, "\u8c03\u6574\u8bb0\u5f55\u5df2\u4fdd\u5b58")
            except Exception as exc:
                messages.error(request, f"\u8c03\u6574\u8bb0\u5f55\u4fdd\u5b58\u5931\u8d25\uff1a{exc}")
            return redirect("contract_adjustment_list")

        if form_type == "update_adjustment_status":
            adjustment_id = request.POST.get("adjustment_id", "").strip()
            to_status = request.POST.get("to_status", "").strip()
            comment = request.POST.get("comment", "").strip()
            return_reason = request.POST.get("return_reason", "").strip()
            try:
                adjustment = ContractAdjustment.objects.select_related("contract").get(id=adjustment_id)
                from_status = adjustment.approval_status
                with transaction.atomic():
                    adjustment.approval_status = to_status
                    adjustment.approval_comment = comment
                    if to_status == "RETURNED":
                        adjustment.return_reason = return_reason
                    if to_status == "IN_REVIEW":
                        adjustment.submitted_by = request.user
                        adjustment.submitted_at = timezone.now()
                    if to_status == "APPROVED":
                        adjustment.approver = request.user
                        adjustment.approved_at = timezone.now()
                    adjustment.updated_by = request.user.username
                    adjustment.save()
                    if to_status == "APPROVED" and from_status != "APPROVED":
                        _apply_adjustment_to_contract(adjustment)
                    action_type = "EDIT"
                    if to_status == "IN_REVIEW":
                        action_type = "SUBMIT"
                    elif to_status == "APPROVED":
                        action_type = "APPROVE"
                    elif to_status == "RETURNED":
                        action_type = "RETURN"
                    _log_adjustment_action(
                        adjustment, action_type, request.user,
                        comment=comment, from_status=from_status, to_status=to_status,
                    )
                messages.success(request, "\u8c03\u6574\u72b6\u6001\u5df2\u66f4\u65b0")
            except Exception as exc:
                messages.error(request, f"\u8c03\u6574\u72b6\u6001\u66f4\u65b0\u5931\u8d25\uff1a{exc}")
            return redirect("contract_adjustment_list")

    filters = {
        "adj_ct_code": request.GET.get("adj_ct_code", "").strip(),
        "adjustment_type": request.GET.get("adjustment_type", "").strip(),
        "approval_status": request.GET.get("approval_status", "").strip(),
        "adjustment_no": request.GET.get("adjustment_no", "").strip(),
    }
    qs = ContractAdjustment.objects.select_related(
        "contract", "project", "before_counterparty", "after_counterparty"
    )
    if filters["adj_ct_code"]:
        qs = qs.filter(contract_ct_code_snapshot__icontains=filters["adj_ct_code"])
    if filters["adjustment_type"]:
        qs = qs.filter(adjustment_type=filters["adjustment_type"])
    if filters["approval_status"]:
        qs = qs.filter(approval_status=filters["approval_status"])
    if filters["adjustment_no"]:
        qs = qs.filter(adjustment_no__icontains=filters["adjustment_no"])

    context = {
        "adjustments": list(qs.order_by("-created_at")[:300]),
        "contracts": ContractMaster.objects.filter(is_deleted=False).order_by("-contract_ct_code"),
        "counterparties": Counterparty.objects.filter(status="ACTIVE").order_by("party_name"),
        "filters": filters,
        "permissions": permissions,
        "adjustment_type_choices": ADJUSTMENT_TYPE_CHOICES,
        "approval_status_choices": APPROVAL_STATUS_CHOICES,
        "source_system_choices": SOURCE_SYSTEM_CHOICES,
        "in_review_count": qs.filter(approval_status="IN_REVIEW").count(),
        "returned_count": qs.filter(approval_status="RETURNED").count(),
        "active_menu": "contract_adjustment",
    }
    return render(request, "contract_adjustment.html", context)


# ---------------------------------------------------------------------------
# 导入视图
# ---------------------------------------------------------------------------

@login_required
def import_counterparty_ledger(request):
    if request.method != "POST":
        return redirect("contract_counterparty_list")

    mode = request.POST.get("mode", "insert").strip().lower()
    file = request.FILES.get("import_file")
    if not file:
        messages.error(request, "\u8bf7\u9009\u62e9\u5f80\u6765\u5355\u4f4d\u53f0\u8d26\u6587\u4ef6")
        return redirect("contract_counterparty_list")

    if mode not in {"insert", "upsert"}:
        messages.error(request, "\u5bfc\u5165\u6a21\u5f0f\u4e0d\u5408\u6cd5")
        return redirect("contract_counterparty_list")

    wb = load_workbook(file, data_only=True)
    ws = wb.active
    headers = [str(c.value).strip() if c.value else "" for c in ws[1]]
    mapping = {
        "\u5355\u4f4d\u540d\u79f0": "party_name",
        "\u5355\u4f4d\u7c7b\u578b": "party_type",
        "\u7edf\u4e00\u793e\u4f1a\u4fe1\u7528\u4ee3\u7801": "credit_code",
        "\u8054\u7cfb\u4eba": "contact_name",
        "\u8054\u7cfb\u7535\u8bdd": "contact_phone",
        "\u72b6\u6001": "status",
        "\u5907\u6ce8": "remark",
    }
    idx_map = {}
    for idx, header in enumerate(headers):
        if header in mapping:
            idx_map[mapping[header]] = idx

    for field in ["party_name", "party_type", "credit_code"]:
        if field not in idx_map:
            messages.error(request, f"\u5f80\u6765\u5355\u4f4d\u5bfc\u5165\u7f3a\u5c11\u5fc5\u8981\u5217\uff1a{field}")
            return redirect("contract_counterparty_list")

    created = updated = skipped = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        row_data = {
            field: str(row[idx] if idx < len(row) and row[idx] is not None else "").strip()
            for field, idx in idx_map.items()
        }
        if not row_data.get("credit_code"):
            skipped += 1
            continue
        code = row_data["credit_code"].upper()
        defaults = {
            "party_name": row_data.get("party_name", ""),
            "party_type": row_data.get("party_type", "OTHER_VENDOR"),
            "contact_name": row_data.get("contact_name", ""),
            "contact_phone": row_data.get("contact_phone", ""),
            "status": row_data.get("status", "ACTIVE") or "ACTIVE",
            "remark": row_data.get("remark", ""),
        }
        obj = Counterparty.objects.filter(credit_code=code).first()
        if obj and mode == "insert":
            skipped += 1
            continue
        if obj and mode == "upsert":
            for key, value in defaults.items():
                setattr(obj, key, value)
            obj.updated_by = request.user.username
            obj.save()
            updated += 1
            continue
        Counterparty.objects.create(credit_code=code, created_by=request.user.username, updated_by=request.user.username, **defaults)
        created += 1

    messages.success(request, f"\u5f80\u6765\u5355\u4f4d\u5bfc\u5165\u5b8c\u6210\uff1a\u65b0\u589e {created} \u6761\uff0c\u66f4\u65b0 {updated} \u6761\uff0c\u8df3\u8fc7 {skipped} \u6761")
    return redirect("contract_counterparty_list")


@login_required
def import_contract_ledger(request):
    if request.method != "POST":
        return redirect("contract_list")

    mode = request.POST.get("mode", "insert").strip().lower()
    file = request.FILES.get("import_file")
    if not file:
        messages.error(request, "\u8bf7\u9009\u62e9\u5408\u540c\u53f0\u8d26\u6587\u4ef6")
        return redirect("contract_list")

    if mode not in {"insert", "upsert"}:
        messages.error(request, "\u5bfc\u5165\u6a21\u5f0f\u4e0d\u5408\u6cd5")
        return redirect("contract_list")

    wb = load_workbook(file, data_only=True)
    ws = wb.active
    headers = [str(c.value).strip() if c.value else "" for c in ws[1]]
    mapping = {
        "\u9879\u76ee\u4e3b\u6570\u636e\u7f16\u7801": "project_code",
        "\u5408\u540cCT\u7801": "contract_ct_code",
        "\u5408\u540c\u540d\u79f0": "contract_name",
        "\u7edf\u4e00\u793e\u4f1a\u4fe1\u7528\u4ee3\u7801": "credit_code",
        "\u6765\u6e90\u7cfb\u7edf": "source_system",
        "\u5408\u540c\u65b9\u5411": "contract_direction",
        "\u5408\u540c\u5206\u7c7b": "contract_category",
        "\u5408\u540c\u5e74\u4efd": "contract_year",
        "\u539f\u59cb\u542b\u7a0e\u91d1\u989d": "original_amount_tax",
        "\u539f\u59cb\u4e0d\u542b\u7a0e\u91d1\u989d": "original_amount_notax",
        "\u539f\u59cb\u7a0e\u7387": "original_tax_rate",
        "\u5f53\u524d\u542b\u7a0e\u91d1\u989d": "current_amount_tax",
        "\u5f53\u524d\u4e0d\u542b\u7a0e\u91d1\u989d": "current_amount_notax",
        "\u5f53\u524d\u7a0e\u7387": "current_tax_rate",
        "\u5408\u540c\u72b6\u6001": "contract_status",
        "\u5907\u6ce8": "remark",
    }
    idx_map = {}
    for idx, header in enumerate(headers):
        if header in mapping:
            idx_map[mapping[header]] = idx

    for field in ["project_code", "contract_ct_code", "contract_name", "credit_code",
                  "source_system", "contract_direction", "contract_category"]:
        if field not in idx_map:
            messages.error(request, f"\u5408\u540c\u5bfc\u5165\u7f3a\u5c11\u5fc5\u8981\u5217\uff1a{field}")
            return redirect("contract_list")

    created = updated = skipped = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        row_data = {
            field: str(row[idx] if idx < len(row) and row[idx] is not None else "").strip()
            for field, idx in idx_map.items()
        }
        ct_code = row_data.get("contract_ct_code", "").upper()
        if not CT_CODE_PATTERN.fullmatch(ct_code):
            skipped += 1
            continue
        project = ProjectMaster.objects.filter(
            project_code=row_data.get("project_code", ""), is_deleted=False
        ).first()
        counterparty = Counterparty.objects.filter(
            credit_code=row_data.get("credit_code", "").upper()
        ).first()
        if not project or not counterparty:
            skipped += 1
            continue
        try:
            defaults = {
                "project": project,
                "counterparty": counterparty,
                "contract_name": row_data.get("contract_name", ""),
                "source_system": row_data.get("source_system", "MANUAL"),
                "contract_direction": row_data.get("contract_direction", "NONE"),
                "contract_category": row_data.get("contract_category", "OTHER"),
                "undertaking_dept_code": "",
                "undertaking_dept_name": dept_name_map.get(project.dept, project.dept or ""),
                "contract_year": row_data.get("contract_year", ""),
                "original_amount_tax": _to_decimal(row_data.get("original_amount_tax", "0")),
                "original_amount_notax": _to_decimal(row_data.get("original_amount_notax", "0")),
                "original_tax_rate": _to_decimal(row_data.get("original_tax_rate"), default="0") if row_data.get("original_tax_rate") else None,
                "current_amount_tax": _to_decimal(row_data.get("current_amount_tax") or row_data.get("original_amount_tax", "0")),
                "current_amount_notax": _to_decimal(row_data.get("current_amount_notax") or row_data.get("original_amount_notax", "0")),
                "current_tax_rate": _to_decimal(row_data.get("current_tax_rate"), default="0") if row_data.get("current_tax_rate") else None,
                "contract_status": row_data.get("contract_status", "SIGNED") or "SIGNED",
                "remark": row_data.get("remark", ""),
            }
        except InvalidOperation:
            skipped += 1
            continue

        obj = ContractMaster.objects.filter(contract_ct_code=ct_code).first()
        if obj and mode == "insert":
            skipped += 1
            continue
        if obj and mode == "upsert":
            for key, value in defaults.items():
                setattr(obj, key, value)
            obj.updated_by = request.user.username
            obj.full_clean()
            obj.save()
            updated += 1
            continue
        new_contract = ContractMaster(contract_ct_code=ct_code, created_by=request.user.username, updated_by=request.user.username, **defaults)
        new_contract.full_clean()
        new_contract.save()
        created += 1

    messages.success(request, f"\u5408\u540c\u53f0\u8d26\u5bfc\u5165\u5b8c\u6210\uff1a\u65b0\u589e {created} \u6761\uff0c\u66f4\u65b0 {updated} \u6761\uff0c\u8df3\u8fc7 {skipped} \u6761")
    return redirect("contract_list")