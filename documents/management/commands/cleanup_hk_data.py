from django.core.management.base import BaseCommand, CommandError
from documents.models import ProjectMaster, ProjectMasterLog
from django.utils import timezone


class Command(BaseCommand):
    help = "删除用户 HK 导入的所有项目数据"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="确认执行删除操作",
        )

    def handle(self, *args, **options):
        if not options["confirm"]:
            self.stdout.write(
                self.style.WARNING(
                    "警告：此操作将删除用户 HK 导入的所有项目数据！\n"
                    "请使用 --confirm 参数确认执行。"
                )
            )
            # 显示将要删除的数据统计
            hk_projects = ProjectMaster.objects.filter(created_by="HK")
            self.stdout.write(f"\n将要删除的项目数量：{hk_projects.count()}")
            
            if hk_projects.exists():
                self.stdout.write("\n项目列表：")
                for proj in hk_projects[:20]:
                    self.stdout.write(f"  - {proj.project_code}: {proj.project_name}")
                if hk_projects.count() > 20:
                    self.stdout.write(f"  ... 还有 {hk_projects.count() - 20} 条")
            return

        # 执行删除
        hk_projects = list(ProjectMaster.objects.filter(created_by="HK"))
        
        if not hk_projects:
            self.stdout.write(self.style.SUCCESS("未找到用户 HK 的项目数据"))
            return

        self.stdout.write(f"开始删除 {len(hk_projects)} 个项目数据...")

        deleted_count = 0
        for project in hk_projects:
            # 物理删除
            project.delete()
            deleted_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ 成功删除 {deleted_count} 个项目数据"
            )
        )
