from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("documents/", views.project_master_list, name="project_master_list"),
    path("documents/export-template/", views.export_project_template, name="export_project_template"),
    path("documents/export-list/", views.export_project_list, name="export_project_list"),
    path("documents/import/", views.import_project_master, name="import_project_master"),
    path("documents/<str:project_code>/edit/", views.project_master_edit, name="project_master_edit"),
    # path("documents/<str:project_code>/delete/", views.project_master_delete, name="project_master_delete"),  # 已改为审批流程
    path("documents/submit-delete-approval/", views.submit_delete_approval, name="submit_delete_approval"),
    path("documents/approvals/", views.approval_list, name="approval_list"),
    path("documents/approvals/<int:approval_id>/action/", views.approve_action, name="approve_action"),
    path("documents/users/", views.user_list, name="user_list"),
    path("logout/", views.logout_view, name="logout"),
]
