from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = '设置倪明珠为管理员'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username='倪明珠')
            user.is_staff = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'用户 "{user.username}" 已成功设置为管理员'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('用户 "倪明珠" 不存在'))
