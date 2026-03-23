from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0006_alter_userprofile_can_view_project_list'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='标签名')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
            ],
            options={
                'verbose_name': '标签',
                'verbose_name_plural': '标签',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('article_type', models.CharField(
                    choices=[('note', '学习笔记'), ('essay', '技术随笔')],
                    max_length=10,
                    verbose_name='类型',
                )),
                ('title', models.CharField(max_length=200, verbose_name='标题')),
                ('content', models.TextField(verbose_name='正文（Markdown）')),
                ('category', models.CharField(blank=True, max_length=50, verbose_name='分类')),
                ('is_published', models.BooleanField(default=False, verbose_name='是否发布')),
                ('published_at', models.DateTimeField(blank=True, null=True, verbose_name='发布时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('tags', models.ManyToManyField(blank=True, to='documents.tag', verbose_name='标签')),
            ],
            options={
                'verbose_name': '文章',
                'verbose_name_plural': '文章',
                'ordering': ['-published_at', '-created_at'],
            },
        ),
    ]
