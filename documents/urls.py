from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('documents/', views.project_master_list, name='project_master_list'),  # 后台数据库页面
]