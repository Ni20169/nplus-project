from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from documents.models import UserProfile


class Command(BaseCommand):
    help = "创建默认用户与部门信息（若不存在）"

    def handle(self, *args, **options):
        defaults = [
            ("HK", "###HK123", "临时组"),
            ("钟云海", "zyh@12345", "采购管理部"),
            ("杨晓辉", "yxh@12345", "采购管理部"),
            ("倪明珠", "nmz@12345", "采购管理部"),
        ]

        for username, password, dept in defaults:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"is_active": True},
            )
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
                self.stdout.write(self.style.SUCCESS(f"已创建用户 {username}"))
            else:
                self.stdout.write(f"用户 {username} 已存在")

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.department = dept
            profile.save(update_fields=["department"])

        admin_user = User.objects.filter(username="admin").first()
        if admin_user:
            profile, _ = UserProfile.objects.get_or_create(user=admin_user)
            profile.department = "管理员"
            profile.save(update_fields=["department"])
            self.stdout.write("已更新 admin 部门为 管理员")
