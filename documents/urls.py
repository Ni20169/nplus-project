from django.urls import path
from . import views
from . import contract_views

urlpatterns = [
    # 公开首页
    path("", views.public_home, name="home"),
    # 隐蔽登录入口（不出现在公开页面任何链接中）
    path("nplus-portal/", views.login_view, name="login"),
    # 公开文章页
    path("notes/", views.article_list, name="article_list"),
    path("notes/<int:pk>/", views.article_detail, name="article_detail"),
    # 文章管理（仅 superuser）
    path("notes/create/", views.article_create, name="article_create"),
    path("notes/<int:pk>/edit/", views.article_edit, name="article_edit"),
    path("notes/<int:pk>/delete/", views.article_delete, name="article_delete"),
    # 内部系统（需登录）
    path("documents/", views.project_master_list, name="project_master_list"),
    path("documents/export-template/", views.export_project_template, name="export_project_template"),
    path("documents/export-list/", views.export_project_list, name="export_project_list"),
    path("documents/import/", views.import_project_master, name="import_project_master"),
    path("documents/<str:project_code>/edit/", views.project_master_edit, name="project_master_edit"),
    path("documents/submit-delete-approval/", views.submit_delete_approval, name="submit_delete_approval"),
    path("documents/approvals/", views.approval_list, name="approval_list"),
    path("documents/approvals/<int:approval_id>/action/", views.approve_action, name="approve_action"),
    path("documents/users/", views.user_list, name="user_list"),
    path("documents/permissions/", views.permission_manage, name="permission_manage"),
    path("documents/contracts/counterparties/", contract_views.contract_counterparty_view, name="contract_counterparty_list"),
    path("documents/contracts/list/", contract_views.contract_list_view, name="contract_list"),
    path("documents/contracts/adjustments/", contract_views.contract_adjustment_view, name="contract_adjustment_list"),
    path("documents/contracts/template/counterparty/", contract_views.export_counterparty_template, name="export_counterparty_template"),
    path("documents/contracts/template/contract/", contract_views.export_contract_template, name="export_contract_template"),
    path("documents/contracts/import/counterparty/", contract_views.import_counterparty_ledger, name="import_counterparty_ledger"),
    path("documents/contracts/import/contract/", contract_views.import_contract_ledger, name="import_contract_ledger"),
    path("logout/", views.logout_view, name="logout"),
]
