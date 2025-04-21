from smtplib import SMTPException
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.timezone import now
from django.contrib.auth.forms import PasswordChangeForm
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
from .forms import RegisterForm, CustomRegisterForm, TaskForm
from .models import Task, CustomUser, PasswordResetCode, Category, EmailChangeCode
import json
from datetime import datetime
import random
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

@login_required
def request_password_reset(request):
    if request.method == 'POST':
        email = request.POST.get('email').strip().lower()
        current_email = request.user.email.strip().lower()

        if email != current_email:
            messages.error(request, "Введённый email не совпадает с указанным в вашем профиле.")
            return redirect('request_password_reset')

        # Email совпадает — отправляем код
        code = str(random.randint(100000, 999999))
        PasswordResetCode.objects.create(user=request.user, code=code)

        send_mail(
            'Код сброса пароля',
            f'Ваш код сброса пароля: {code}',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False
        )

        request.session['reset_email'] = email
        return redirect('reset_password')

    return render(request, 'core/request_reset.html')

def request_email_change(request):
    if request.method == 'POST':
        new_email = request.POST.get('new_email')
        user = request.user
        code = str(random.randint(100000, 999999))

        EmailChangeCode.objects.create(user=user, new_email=new_email, code=code)

        send_mail(
            'Подтверждение смены почты',
            f'Вы запросили смену почты. Код подтверждения: {code}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],  # отправляется на старую почту!
            fail_silently=False
        )

        request.session['pending_email'] = new_email
        return redirect('confirm_email_change')

    return render(request, 'core/request_email_change.html')

def confirm_email_change(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        user = request.user
        new_email = request.session.get('pending_email')

        confirmation = EmailChangeCode.objects.filter(user=user, new_email=new_email, code=code).last()
        if confirmation:
            user.email = new_email
            user.save()
            confirmation.delete()
            messages.success(request, "Почта успешно изменена.")
            return redirect('profile')
        else:
            messages.error(request, "Неверный код.")

    return render(request, 'core/confirm_email_change.html')

def reset_password(request):
    email = request.session.get('reset_email')  # ← используем email из сессии

    if request.method == 'POST':
        code = request.POST.get('code')
        new_password = request.POST.get('password')

        try:
            user = CustomUser.objects.get(email=email)
            reset_code = PasswordResetCode.objects.filter(user=user, code=code).last()

            if reset_code:
                user.set_password(new_password)
                user.save()
                reset_code.delete()
                messages.success(request, "Пароль обновлён. Войдите с новым паролем.")
                return redirect('login')
            else:
                messages.error(request, "Неверный код.")
        except CustomUser.DoesNotExist:
            messages.error(request, "Пользователь не найден.")
    return render(request, 'core/reset_password.html')

@login_required
def profile_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        notifications = request.POST.get('receive_notifications') == 'on'

        if username:
            request.user.username = username
        if email:
            # Проверим, используется ли email другим пользователем
            if CustomUser.objects.filter(email=email).exclude(pk=request.user.pk).exists():
                messages.error(request, "Эта почта уже занята другим пользователем.")
                return redirect('profile')
            request.user.email = email

        request.user.receive_notifications = notifications
        try:
            request.user.save()
            messages.success(request, "Профиль обновлён.")
        except IntegrityError:
            messages.error(request, "Ошибка сохранения. Возможно, вы указали занятый email.")
        return redirect('profile')

    return render(request, 'core/profile.html')

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect('profile')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'core/change_password.html', {'form': form})

@login_required
def activity_calendar_data(request):
    tasks = Task.objects.filter(user=request.user)

    events = []
    for task in tasks:
        color = {
            'planned': '#6c757d',        # серый
            'in_progress': '#0d6efd',    # синий
            'done': '#198754',           # зелёный
        }.get(task.status, '#6c757d')

        events.append({
            'title': task.title,
            'start': task.due_date.strftime('%Y-%m-%d'),
            'color': color,
            'extendedProps': {
                    'status': task.get_status_display(),
                    'task_id': task.id
            }
        })

    return JsonResponse(events, safe=False)

@login_required
def activity_view(request):
    user = request.user
    today = now().date()

    # График по выполненным задачам
    done_data = (
        Task.objects
        .filter(user=user, status='done')
        .annotate(date=TruncDate('completed_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    done_labels = [entry['date'].strftime('%Y-%m-%d') for entry in done_data]
    done_counts = [entry['count'] for entry in done_data]

    # Просроченные задачи (не выполнены и дедлайн в прошлом)
    overdue = Task.objects.filter(user=user, status__in=['planned', 'in_progress'], due_date__lt=today).count()

    # Невыполненные задачи (не статус 'done')
    not_done = Task.objects.filter(user=user).exclude(status='done').count()

    # Всего задач и выполнено
    total = Task.objects.filter(user=user).count()
    completed = Task.objects.filter(user=user, status='done').count()
    remaining = Task.objects.filter(user=user).exclude(status='done').count()
    percent = int((completed / total) * 100) if total > 0 else 0

    return render(request, 'core/activity.html', {
        'done_labels': done_labels,
        'done_counts': done_counts,
        'overdue': overdue,
        'not_done': not_done,
        'total': total,
        'completed': completed,
        'remaining': remaining,
        'percent': percent,
    })

@login_required
def update_task_status(request, pk, new_status):
    task = Task.objects.get(pk=pk, user=request.user)
    task.status = new_status
    if new_status == 'done':
        task.completed = True
        task.completed_at = now()
    else:
        task.completed = False
        task.completed_at = None
    task.save()
    return HttpResponseRedirect(reverse('tasks'))


@login_required
def activity_view(request):
    user = request.user
    today = now().date()

    tasks = Task.objects.filter(user=user)

    total = tasks.count()
    completed = tasks.filter(status='done').count()
    remaining = tasks.exclude(status='done').count()
    overdue = tasks.filter(status__in=['planned', 'in_progress'], due_date__lt=today).count()

    # Для графика по дням (выполненные)
    done_tasks = tasks.filter(status='done', completed_at__isnull=False)
    done_data = {}
    for task in done_tasks:
        day = task.completed_at.date()
        done_data[day] = done_data.get(day, 0) + 1

    done_labels = list(map(str, sorted(done_data.keys())))
    done_counts = [done_data[day] for day in sorted(done_data.keys())]

    # Для графика по статусам
    in_progress = tasks.filter(status='in_progress').count()
    not_done = tasks.filter(status='planned').count()

    return render(request, 'core/activity.html', {
        'total': total,
        'completed': completed,
        'remaining': remaining,
        'overdue': overdue,
        'done_labels': done_labels,
        'done_counts': done_counts,
        'not_done': not_done,
        'in_progress': in_progress,
    })

@login_required
def task_list(request):
    tasks_qs = Task.objects.filter(user=request.user)

    category_id = request.GET.get('category')
    if category_id:
        tasks_qs = tasks_qs.filter(categories__id=category_id)

    sort = request.GET.get('sort', 'title')
    order = request.GET.get('order', 'asc')
    ordering = sort if order == 'asc' else f"-{sort}"
    tasks_qs = tasks_qs.order_by(ordering)

    # Пагинация
    paginator = Paginator(tasks_qs, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.filter(user=request.user)
    selected_category = int(category_id) if category_id else None

    return render(request, 'core/tasks.html', {
        'tasks': page_obj,
        'categories': categories,
        'selected_category': selected_category,
    })

@login_required
@login_required
def task_create(request):
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            form.save_m2m()
            return redirect('tasks')
    else:
        form = TaskForm(user=request.user)
    return render(request, 'core/task_form.html', {'form': form})


@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('tasks')
    else:
        form = TaskForm(instance=task, user=request.user)
    return render(request, 'core/task_form.html', {'form': form})

@login_required
def task_delete(request, pk):
    task = Task.objects.get(pk=pk, user=request.user)
    if request.method == 'POST':
        task.delete()
        return redirect('tasks')
    return render(request, 'core/task_confirm_delete.html', {'task': task})


def register_view(request):
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            email = user.email

            try:
                # Пытаемся отправить письмо
                send_mail(
                    'Подтверждение почты',
                    'Спасибо за регистрацию в Flowvance!',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )

                user.save()
                login(request, user)
                return redirect('home')

            except SMTPException:
                messages.error(request, "Ошибка: Почтовый ящик недоступен или не существует.")
            except Exception:
                messages.error(request, "Не удалось отправить письмо. Проверьте корректность email.")
    else:
        form = CustomRegisterForm()

    return render(request, 'core/register.html', {'form': form})

@login_required
def home(request):
    return render(request, 'core/home.html')

@login_required
def category_list(request):
    categories = Category.objects.filter(user=request.user)
    return render(request, 'core/categories.html', {'categories': categories})

@login_required
def category_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Category.objects.create(name=name, user=request.user)
            return redirect('category_list')
    return render(request, 'core/category_form.html')

@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    category.delete()
    return redirect('category_list')

@login_required
def assign_category(request, task_id):
    task = get_object_or_404(Task, pk=task_id, user=request.user)

    if request.method == 'POST':
        category_id = request.POST.get('category_id')

        # Очищаем все текущие категории
        task.categories.clear()

        if category_id:
            try:
                category = Category.objects.get(id=category_id, user=request.user)
                task.categories.add(category)
            except Category.DoesNotExist:
                pass

    return redirect('tasks')