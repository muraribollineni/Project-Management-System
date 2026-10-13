from django.urls import path

from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('new/', views.project_create, name='project_create'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/edit/', views.project_update, name='project_update'),
    path('<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('<int:pk>/members/add/', views.member_add, name='member_add'),
    path('<int:pk>/members/<int:membership_id>/remove/', views.member_remove, name='member_remove'),
]