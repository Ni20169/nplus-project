from django.urls import path
from . import views
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("documents/", views.project_master_list, name="project_master_list"),
    path("documents/export-template/", views.export_project_template, name="export_project_template"),
    path("documents/import/", views.import_project_master, name="import_project_master"),
    path("documents/<str:project_code>/edit/", views.project_master_edit, name="project_master_edit"),
    path("documents/<str:project_code>/delete/", views.project_master_delete, name="project_master_delete"),
    path("documents/users/", views.user_list, name="user_list"),
    path("logout/", views.logout_view, name="logout"),
]
