from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

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
    path('tasks/status/<int:pk>/<str:new_status>/', views.update_task_status, name='update_task_status'),
    path('activity/calendar/data/', views.activity_calendar_data, name='activity_calendar_data'),
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/new/', views.category_create, name='category_create'),
    path('categories/delete/<int:pk>/', views.category_delete, name='category_delete'),
    path('tasks/assign-category/<int:task_id>/', views.assign_category, name='assign_category'),
    path('profile/change-email/', views.request_email_change, name='request_email_change'),
    path('profile/change-email/confirm/', views.confirm_email_change, name='confirm_email_change'),
    path('home/tasks/', views.home_tasks_ajax, name='home_tasks_ajax'),
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='core/password_reset_form.html',
             email_template_name='core/password_reset_email.html',
             subject_template_name='core/password_reset_subject.txt',
             success_url='done/'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='core/password_reset_done.html'),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='core/password_reset_confirm.html',
             success_url='/login/'
         ),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='core/password_reset_complete.html'),
         name='password_reset_complete'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
