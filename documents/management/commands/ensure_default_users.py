from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "创建默认访客用户HK（若不存在）"

    def handle(self, *args, **options):
        username = "HK"
        password = "###HK123"

        user, created = User.objects.get_or_create(username=username, defaults={"is_active": True})
        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS("已创建访客用户 HK"))
        else:
            self.stdout.write("访客用户 HK 已存在")
