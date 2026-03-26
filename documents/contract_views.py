import re
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from openpyxl import load_workbook

from .models import (
    ADJUSTMENT_TYPE_CHOICES,
    APPROVAL_STATUS_CHOICES,
    CONTRACT_CATEGORY_CHOICES,
    CONTRACT_DIRECTION_CHOICES,
    CONTRACT_STATUS_CHOICES,
    SOURCE_SYSTEM_CHOICES,
    ContractAdjustment,
    ContractAdjustmentActionLog,
    ContractMaster,
    Counterparty,
    ProjectMaster,
)

CT_CODE_PATTERN = re.compile(r"^CT\d{12}$")


def _to_decimal(value, default="0"):
    text = str(value if value is not None else "").strip()
    if text == "":
        text = default
    return Decimal(text)


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


@login_required
def contract_module(request):
    projects = ProjectMaster.objects.filter(is_deleted=False).order_by("-project_code")
    counterparties = Counterparty.objects.all().order_by("party_name")
    contracts_qs = ContractMaster.objects.filter(is_deleted=False).select_related("project", "counterparty")
    adjustments_qs = ContractAdjustment.objects.select_related("contract", "project", "before_counterparty", "after_counterparty")

    contract_filters = {
        "project_code": request.GET.get("project_code", "").strip(),
        "project_name": request.GET.get("project_name", "").strip(),
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

    if contract_filters["project_code"]:
        contracts_qs = contracts_qs.filter(project_code_snapshot__icontains=contract_filters["project_code"])
    if contract_filters["project_name"]:
        contracts_qs = contracts_qs.filter(project__project_name__icontains=contract_filters["project_name"])
    if contract_filters["contract_ct_code"]:
        contracts_qs = contracts_qs.filter(contract_ct_code__icontains=contract_filters["contract_ct_code"])
    if contract_filters["contract_name"]:
        contracts_qs = contracts_qs.filter(contract_name__icontains=contract_filters["contract_name"])
    if contract_filters["source_system"]:
        contracts_qs = contracts_qs.filter(source_system=contract_filters["source_system"])
    if contract_filters["contract_direction"]:
        contracts_qs = contracts_qs.filter(contract_direction=contract_filters["contract_direction"])
    if contract_filters["contract_category"]:
        contracts_qs = contracts_qs.filter(contract_category=contract_filters["contract_category"])
    if contract_filters["contract_status"]:
        contracts_qs = contracts_qs.filter(contract_status=contract_filters["contract_status"])
    if contract_filters["undertaking_dept"]:
        contracts_qs = contracts_qs.filter(
            Q(undertaking_dept_code__icontains=contract_filters["undertaking_dept"])
            | Q(undertaking_dept_name__icontains=contract_filters["undertaking_dept"])
        )
    if contract_filters["contract_year"]:
        contracts_qs = contracts_qs.filter(contract_year__icontains=contract_filters["contract_year"])
    if contract_filters["counterparty_name"]:
        contracts_qs = contracts_qs.filter(counterparty_name_snapshot__icontains=contract_filters["counterparty_name"])

    adjustment_filters = {
        "adj_ct_code": request.GET.get("adj_ct_code", "").strip(),
        "adjustment_type": request.GET.get("adjustment_type", "").strip(),
        "approval_status": request.GET.get("approval_status", "").strip(),
    }

    if adjustment_filters["adj_ct_code"]:
        adjustments_qs = adjustments_qs.filter(contract_ct_code_snapshot__icontains=adjustment_filters["adj_ct_code"])
    if adjustment_filters["adjustment_type"]:
        adjustments_qs = adjustments_qs.filter(adjustment_type=adjustment_filters["adjustment_type"])
    if adjustment_filters["approval_status"]:
        adjustments_qs = adjustments_qs.filter(approval_status=adjustment_filters["approval_status"])

    if request.method == "POST":
        form_type = request.POST.get("form_type", "").strip()

        if form_type == "create_counterparty":
            try:
                with transaction.atomic():
                    Counterparty.objects.create(
                        party_name=request.POST.get("party_name", "").strip(),
                        party_type=request.POST.get("party_type", "").strip(),
                        credit_code=request.POST.get("credit_code", "").strip().upper(),
                        contact_name=request.POST.get("contact_name", "").strip(),
                        contact_phone=request.POST.get("contact_phone", "").strip(),
                        status=request.POST.get("status", "ACTIVE").strip() or "ACTIVE",
                        remark=request.POST.get("remark", "").strip(),
                    )
                messages.success(request, "往来单位已新增")
            except Exception as exc:
                messages.error(request, f"往来单位保存失败: {exc}")
            return redirect("contract_module")

        if form_type == "create_contract":
            project_id = request.POST.get("project_id", "").strip()
            counterparty_id = request.POST.get("counterparty_id", "").strip()
            ct_code = request.POST.get("contract_ct_code", "").strip().upper()
            if not CT_CODE_PATTERN.fullmatch(ct_code):
                messages.error(request, "CT码格式错误，必须为CT+12位数字")
                return redirect("contract_module")
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
                        undertaking_dept_code=request.POST.get("undertaking_dept_code", "").strip(),
                        undertaking_dept_name=request.POST.get("undertaking_dept_name", "").strip(),
                        contract_year=request.POST.get("contract_year", "").strip(),
                        sign_date=request.POST.get("sign_date") or None,
                        effective_date=request.POST.get("effective_date") or None,
                        close_date=request.POST.get("close_date") or None,
                        original_amount_tax=_to_decimal(request.POST.get("original_amount_tax", "0")),
                        original_amount_notax=_to_decimal(request.POST.get("original_amount_notax", "0")),
                        original_tax_rate=_to_decimal(request.POST.get("original_tax_rate", "0"), default="0") if request.POST.get("original_tax_rate", "").strip() else None,
                        current_amount_tax=_to_decimal(request.POST.get("current_amount_tax", "0")),
                        current_amount_notax=_to_decimal(request.POST.get("current_amount_notax", "0")),
                        current_tax_rate=_to_decimal(request.POST.get("current_tax_rate", "0"), default="0") if request.POST.get("current_tax_rate", "").strip() else None,
                        contract_status=request.POST.get("contract_status", "SIGNED").strip() or "SIGNED",
                        remark=request.POST.get("remark", "").strip(),
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
                messages.error(request, f"合同保存失败: {exc}")
            return redirect("contract_module")

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
                        after_tax_rate=_to_decimal(request.POST.get("after_tax_rate", "0"), default="0") if request.POST.get("after_tax_rate", "").strip() else None,
                        after_counterparty_id=request.POST.get("after_counterparty_id") or None,
                        remark=request.POST.get("remark", "").strip(),
                        approval_status=request.POST.get("approval_status", "DRAFT").strip() or "DRAFT",
                        submitted_by=request.user,
                        submitted_at=timezone.now(),
                        approver_name="倪明珠",
                        source_system=request.POST.get("source_system", contract.source_system).strip() or contract.source_system,
                        source_record_id=request.POST.get("source_record_id", "").strip(),
                    )
                    adjustment.save()
                    _log_adjustment_action(
                        adjustment,
                        "EDIT",
                        request.user,
                        comment="创建调整记录",
                        from_status="",
                        to_status=adjustment.approval_status,
                    )
                    if adjustment.approval_status == "APPROVED":
                        from_status = adjustment.approval_status
                        _apply_adjustment_to_contract(adjustment)
                        _log_adjustment_action(
                            adjustment,
                            "APPROVE",
                            request.user,
                            comment="录入即通过并同步主表",
                            from_status=from_status,
                            to_status="APPROVED",
                        )
                messages.success(request, "调整记录已保存")
            except Exception as exc:
                messages.error(request, f"调整记录保存失败: {exc}")
            return redirect("contract_module")

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
                    adjustment.save()
                    if to_status == "APPROVED" and from_status != "APPROVED":
                        _apply_adjustment_to_contract(adjustment)
                    action_type = "EDIT"
                    if to_status == "IN_REVIEW":
                        action_type = "SUBMIT"
                    if to_status == "APPROVED":
                        action_type = "APPROVE"
                    if to_status == "RETURNED":
                        action_type = "RETURN"
                    _log_adjustment_action(
                        adjustment,
                        action_type,
                        request.user,
                        comment=comment,
                        from_status=from_status,
                        to_status=to_status,
                    )
                messages.success(request, "调整状态已更新")
            except Exception as exc:
                messages.error(request, f"调整状态更新失败: {exc}")
            return redirect("contract_module")

    contracts = list(contracts_qs.order_by("-created_at")[:200])
    adjustments = list(adjustments_qs.order_by("-created_at")[:200])

    in_review_adjustments = [a for a in adjustments if a.approval_status == "IN_REVIEW"]
    returned_adjustments = [a for a in adjustments if a.approval_status == "RETURNED"]
    approved_adjustments = [a for a in adjustments if a.approval_status == "APPROVED"]

    project_summary = (
        contracts_qs.values("project_code_snapshot", "project__project_name")
        .annotate(
            income_amount=Sum("current_amount_tax", filter=Q(contract_direction="INCOME")),
            expense_amount=Sum("current_amount_tax", filter=Q(contract_direction="EXPENSE")),
            income_count=Count("id", filter=Q(contract_direction="INCOME")),
            expense_count=Count("id", filter=Q(contract_direction="EXPENSE")),
        )
        .order_by("project_code_snapshot")[:100]
    )

    context = {
        "projects": projects,
        "counterparties": counterparties,
        "contracts": contracts,
        "adjustments": adjustments,
        "in_review_adjustments": in_review_adjustments,
        "returned_adjustments": returned_adjustments,
        "approved_adjustments": approved_adjustments,
        "project_summary": project_summary,
        "contract_filters": contract_filters,
        "adjustment_filters": adjustment_filters,
        "source_system_choices": SOURCE_SYSTEM_CHOICES,
        "contract_direction_choices": CONTRACT_DIRECTION_CHOICES,
        "contract_category_choices": CONTRACT_CATEGORY_CHOICES,
        "contract_status_choices": CONTRACT_STATUS_CHOICES,
        "adjustment_type_choices": ADJUSTMENT_TYPE_CHOICES,
        "approval_status_choices": APPROVAL_STATUS_CHOICES,
    }
    return render(request, "contract_module.html", context)


@login_required
def import_counterparty_ledger(request):
    if request.method != "POST":
        return redirect("contract_module")

    mode = request.POST.get("mode", "insert").strip().lower()
    file = request.FILES.get("import_file")
    if not file:
        messages.error(request, "请选择往来单位台账文件")
        return redirect("contract_module")

    if mode not in {"insert", "upsert"}:
        messages.error(request, "导入模式不合法")
        return redirect("contract_module")

    wb = load_workbook(file, data_only=True)
    ws = wb.active
    headers = [str(c.value).strip() if c.value else "" for c in ws[1]]
    mapping = {
        "单位名称": "party_name",
        "单位类型": "party_type",
        "统一社会信用代码": "credit_code",
        "联系人": "contact_name",
        "联系电话": "contact_phone",
        "状态": "status",
        "备注": "remark",
    }
    idx_map = {}
    for idx, header in enumerate(headers):
        if header in mapping:
            idx_map[mapping[header]] = idx

    required_fields = ["party_name", "party_type", "credit_code"]
    for field in required_fields:
        if field not in idx_map:
            messages.error(request, f"往来单位导入缺少必要列: {field}")
            return redirect("contract_module")

    created = 0
    updated = 0
    skipped = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        row_data = {}
        for field, idx in idx_map.items():
            row_data[field] = str(row[idx] if idx < len(row) and row[idx] is not None else "").strip()
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
            obj.save()
            updated += 1
            continue
        Counterparty.objects.create(credit_code=code, **defaults)
        created += 1

    messages.success(request, f"往来单位导入完成：新增{created}条，更新{updated}条，跳过{skipped}条")
    return redirect("contract_module")


@login_required
def import_contract_ledger(request):
    if request.method != "POST":
        return redirect("contract_module")

    mode = request.POST.get("mode", "insert").strip().lower()
    file = request.FILES.get("import_file")
    if not file:
        messages.error(request, "请选择合同台账文件")
        return redirect("contract_module")

    if mode not in {"insert", "upsert"}:
        messages.error(request, "导入模式不合法")
        return redirect("contract_module")

    wb = load_workbook(file, data_only=True)
    ws = wb.active
    headers = [str(c.value).strip() if c.value else "" for c in ws[1]]
    mapping = {
        "项目主数据编码": "project_code",
        "合同CT码": "contract_ct_code",
        "合同名称": "contract_name",
        "统一社会信用代码": "credit_code",
        "来源系统": "source_system",
        "合同方向": "contract_direction",
        "合同分类": "contract_category",
        "承担部门编码": "undertaking_dept_code",
        "承担部门名称": "undertaking_dept_name",
        "合同年份": "contract_year",
        "原始含税金额": "original_amount_tax",
        "原始不含税金额": "original_amount_notax",
        "原始税率": "original_tax_rate",
        "当前含税金额": "current_amount_tax",
        "当前不含税金额": "current_amount_notax",
        "当前税率": "current_tax_rate",
        "合同状态": "contract_status",
        "备注": "remark",
    }

    idx_map = {}
    for idx, header in enumerate(headers):
        if header in mapping:
            idx_map[mapping[header]] = idx

    for field in ["project_code", "contract_ct_code", "contract_name", "credit_code", "source_system", "contract_direction", "contract_category"]:
        if field not in idx_map:
            messages.error(request, f"合同导入缺少必要列: {field}")
            return redirect("contract_module")

    created = 0
    updated = 0
    skipped = 0

    for row in ws.iter_rows(min_row=2, values_only=True):
        row_data = {}
        for field, idx in idx_map.items():
            row_data[field] = str(row[idx] if idx < len(row) and row[idx] is not None else "").strip()

        ct_code = row_data.get("contract_ct_code", "").upper()
        if not CT_CODE_PATTERN.fullmatch(ct_code):
            skipped += 1
            continue

        project = ProjectMaster.objects.filter(project_code=row_data.get("project_code", ""), is_deleted=False).first()
        counterparty = Counterparty.objects.filter(credit_code=row_data.get("credit_code", "").upper()).first()
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
                "undertaking_dept_code": row_data.get("undertaking_dept_code", ""),
                "undertaking_dept_name": row_data.get("undertaking_dept_name", ""),
                "contract_year": row_data.get("contract_year", ""),
                "original_amount_tax": _to_decimal(row_data.get("original_amount_tax", "0")),
                "original_amount_notax": _to_decimal(row_data.get("original_amount_notax", "0")),
                "original_tax_rate": _to_decimal(row_data.get("original_tax_rate", "0"), default="0") if row_data.get("original_tax_rate", "") else None,
                "current_amount_tax": _to_decimal(row_data.get("current_amount_tax", row_data.get("original_amount_tax", "0"))),
                "current_amount_notax": _to_decimal(row_data.get("current_amount_notax", row_data.get("original_amount_notax", "0"))),
                "current_tax_rate": _to_decimal(row_data.get("current_tax_rate", "0"), default="0") if row_data.get("current_tax_rate", "") else None,
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
            obj.full_clean()
            obj.save()
            updated += 1
            continue

        new_contract = ContractMaster(contract_ct_code=ct_code, **defaults)
        new_contract.full_clean()
        new_contract.save()
        created += 1

    messages.success(request, f"合同台账导入完成：新增{created}条，更新{updated}条，跳过{skipped}条")
    return redirect("contract_module")
