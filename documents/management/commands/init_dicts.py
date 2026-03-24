import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from documents.models import DictType, DictItem


DICT_TYPES = [
    ("BUSINESS_UNIT", "业务板块", "基础字典", "业务板块字典", 20),
    ("DEPT", "项目承担部门", "基础字典", "项目承担部门字典", 30),
    ("PROJECT_TYPE", "项目类型", "基础字典", "项目类型字典", 40),
    ("ORG_MODE", "项目组织模式", "基础字典", "项目组织模式字典", 50),
    ("DATA_STATUS", "数据状态", "基础字典", "数据状态字典", 60),
    ("PROVINCE", "省", "行政区划", "省级行政区划", 70),
    ("CITY", "市", "行政区划", "市级行政区划", 80),
]


class Command(BaseCommand):
    help = "初始化字典类型与字典项（读取 documents/dict_items_template.csv）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            dest="csv_path",
            default="documents/dict_items_template.csv",
            help="字典项CSV路径",
        )

    def handle(self, *args, **options):
        created_types = 0
        for code, name, group, desc, order in DICT_TYPES:
            obj, created = DictType.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "group": group,
                    "description": desc,
                    "sort_order": order,
                    "is_active": True,
                },
            )
            if created:
                created_types += 1
        self.stdout.write(self.style.SUCCESS(f"字典类型初始化完成，新建 {created_types} 条。"))

        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            self.stdout.write(self.style.WARNING(f"未找到CSV文件：{csv_path}"))
            return

        created_items = 0
        skipped = 0
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dict_code = (row.get("dict_type") or "").strip()
                code = (row.get("code") or "").strip()
                name = (row.get("name") or "").strip()
                value = (row.get("value") or "").strip()
                parent_code = (row.get("parent_code") or "").strip()
                remark = (row.get("remark") or "").strip()
                sort_order = int((row.get("sort_order") or "0").strip() or 0)
                is_active = str(row.get("is_active") or "true").strip().lower() in ["1", "true", "是", "y", "yes"]

                if not dict_code or not code:
                    skipped += 1
                    continue

                dict_type = DictType.objects.filter(code=dict_code).first()
                if not dict_type:
                    skipped += 1
                    continue

                obj, created = DictItem.objects.get_or_create(
                    dict_type=dict_type,
                    code=code,
                    defaults={
                        "name": name or code,
                        "value": value,
                        "parent_code": parent_code,
                        "sort_order": sort_order,
                        "is_active": is_active,
                        "remark": remark,
                    },
                )
                if created:
                    created_items += 1
        self.stdout.write(self.style.SUCCESS(f"字典项初始化完成，新建 {created_items} 条，跳过 {skipped} 条。"))
