from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.register_view, name='register'),
    path('tasks/', views.task_list, name='tasks'),
    path('tasks/new/', views.task_create, name='task_create'),
    path('tasks/edit/<int:pk>/', views.task_edit, name='task_edit'),
    path('tasks/delete/<int:pk>/', views.task_delete, name='task_delete'),
    path('activity/', views.activity_view, name='activity'),
    path('activity/', views.activity_view, name='activity'),
    path('tasks/status/<int:pk>/<str:new_status>/', views.update_task_status, name='update_task_status'),
    path('activity/calendar/data/', views.activity_calendar_data, name='activity_calendar_data'),
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('reset/request/', views.request_password_reset, name='request_password_reset'),
    path('reset/confirm/', views.reset_password, name='reset_password'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/new/', views.category_create, name='category_create'),
    path('categories/delete/<int:pk>/', views.category_delete, name='category_delete'),
    path('tasks/assign-category/<int:task_id>/', views.assign_category, name='assign_category'),
    path('profile/change-email/', views.request_email_change, name='request_email_change'),
    path('profile/change-email/confirm/', views.confirm_email_change, name='confirm_email_change'),
]
