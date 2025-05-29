from smtplib import SMTPException
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.timezone import now
from django.contrib.auth.forms import PasswordChangeForm
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
from .forms import CustomRegisterForm, TaskForm, ProfileForm
from .models import Task, CustomUser, PasswordResetCode, Category, EmailChangeCode
import random
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

@login_required
def request_password_reset(request):
    if request.method == 'POST':
        email = request.POST.get('email').strip().lower()
        current_email = request.user.email.strip().lower()

        if email != current_email:
            messages.error(request, "Введённый email не совпадает с указанным в вашем профиле.")
            return redirect('request_password_reset')

        # Удаляем старые коды
        PasswordResetCode.objects.filter(user=request.user).delete()
        
        code = str(random.randint(100000, 999999))
        PasswordResetCode.objects.create(user=request.user, code=code)

        try:
            send_mail(
                'Код сброса пароля',
                f'Ваш код сброса пароля: {code}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False
            )
            request.session['reset_email'] = email
            messages.success(request, "Код сброса пароля отправлен на вашу почту.")
            return redirect('reset_password')
        except Exception:
            messages.error(request, "Не удалось отправить код. Попробуйте позже.")

    return render(request, 'core/request_reset.html')

def reset_password(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('request_password_reset')

    if request.method == 'POST':
        code = request.POST.get('code')
        new_password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Проверка совпадения паролей
        if new_password != confirm_password:
            messages.error(request, "Пароли не совпадают.")
            return render(request, 'core/reset_password.html')

        # Проверка сложности пароля
        if len(new_password) < 8:
            messages.error(request, "Пароль должен содержать минимум 8 символов.")
            return render(request, 'core/reset_password.html')
        
        if not any(char.isdigit() for char in new_password):
            messages.error(request, "Пароль должен содержать хотя бы одну цифру.")
            return render(request, 'core/reset_password.html')
        
        if not any(char.isalpha() for char in new_password):
            messages.error(request, "Пароль должен содержать хотя бы одну букву.")
            return render(request, 'core/reset_password.html')

        try:
            user = CustomUser.objects.get(email=email)
            reset_code = PasswordResetCode.objects.filter(user=user, code=code).last()

            if reset_code:
                user.set_password(new_password)
                user.save()
                reset_code.delete()
                del request.session['reset_email']
                messages.success(request, "Пароль успешно обновлён. Войдите с новым паролем.")
                return redirect('login')
            else:
                messages.error(request, "Неверный код.")
        except CustomUser.DoesNotExist:
            messages.error(request, "Пользователь не найден.")

    return render(request, 'core/reset_password.html')

def request_email_change(request):
    if request.method == 'POST':
        new_email = request.POST.get('new_email')
        try:
            validate_email(new_email)
            
            # Проверяем, не занят ли email
            if CustomUser.objects.filter(email=new_email).exists():
                messages.error(request, "Этот email уже используется другим пользователем.")
                return redirect('request_email_change')
            
            # Удаляем старые коды
            EmailChangeCode.objects.filter(user=request.user).delete()
            
            code = str(random.randint(100000, 999999))
            EmailChangeCode.objects.create(user=request.user, new_email=new_email, code=code)

            try:
                send_mail(
                    'Подтверждение смены почты',
                    f'Вы запросили смену почты. Код подтверждения: {code}',
                    settings.DEFAULT_FROM_EMAIL,
                    [request.user.email],
                    fail_silently=False
                )
                request.session['pending_email'] = new_email
                request.session['email_change_attempts'] = 3
                request.session['last_code_sent'] = timezone.now().timestamp()
                return redirect('confirm_email_change')
            except Exception:
                messages.error(request, "Не удалось отправить код. Попробуйте позже.")
        except ValidationError:
            messages.error(request, "Введите корректный email.")
    return render(request, 'core/request_email_change.html')

def confirm_email_change(request):
    if 'pending_email' not in request.session:
        return redirect('request_email_change')
    
    if request.method == 'POST':
        code = request.POST.get('code')
        user = request.user
        new_email = request.session.get('pending_email')
        
        # Проверяем количество попыток
        attempts = request.session.get('email_change_attempts', 3)
        if attempts <= 0:
            messages.error(request, "Превышено количество попыток. Запросите новый код.")
            del request.session['pending_email']
            del request.session['email_change_attempts']
            return redirect('request_email_change')
        
        confirmation = EmailChangeCode.objects.filter(
            user=user,
            new_email=new_email,
            code=code
        ).last()
        
        if confirmation:
            user.email = new_email
            user.save()
            confirmation.delete()
            del request.session['pending_email']
            del request.session['email_change_attempts']
            messages.success(request, "Почта успешно изменена.")
            return redirect('profile')
        
        # Уменьшаем количество попыток
        request.session['email_change_attempts'] = attempts - 1
        messages.error(request, f"Неверный код. Осталось попыток: {attempts - 1}")
    
    # Проверяем, можно ли отправить код повторно
    last_sent = request.session.get('last_code_sent', 0)
    time_passed = timezone.now().timestamp() - last_sent
    can_resend = time_passed >= 60
    
    return render(request, 'core/confirm_email_change.html', {
        'can_resend': can_resend,
        'time_remaining': max(0, 60 - int(time_passed))
    })

@login_required
def profile_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        notifications = request.POST.get('receive_notifications') == 'on'
        avatar = request.FILES.get('avatar')
        remove_avatar = request.POST.get('remove_avatar') == 'on'

        # Проверяем, изменился ли статус уведомлений
        notifications_changed = notifications != request.user.receive_notifications

        if username:
            request.user.username = username

        if email and not CustomUser.objects.filter(email=email).exclude(pk=request.user.pk).exists():
            request.user.email = email
        elif email:
            messages.error(request, "Эта почта уже занята другим пользователем.")
            return redirect('profile')

        request.user.receive_notifications = notifications

        if remove_avatar:
            request.user.avatar.delete(save=False)
            request.user.avatar = None
        elif avatar:
            request.user.avatar = avatar

        request.user.save()

        # Если уведомления были включены, отправляем тестовое уведомление
        if notifications_changed and notifications:
            try:
                send_mail(
                    'Тестовое уведомление',
                    'Поздравляем! Вы успешно включили получение уведомлений в Flowvance. '
                    'Теперь вы будете получать важные уведомления о ваших задачах и событиях.',
                    settings.DEFAULT_FROM_EMAIL,
                    [request.user.email],
                    fail_silently=False
                )
                messages.success(request, "Профиль обновлён. Тестовое уведомление отправлено на вашу почту.")
            except Exception:
                messages.warning(request, "Профиль обновлён, но не удалось отправить тестовое уведомление.")
        else:
            messages.success(request, "Профиль обновлён.")
            
        return redirect('profile')

    return render(request, 'core/profile.html')

@login_required
def change_password(request):
    form = PasswordChangeForm(user=request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        return redirect('profile')
    return render(request, 'core/change_password.html', {'form': form})

@login_required
def activity_calendar_data(request):
    tasks = Task.objects.filter(user=request.user)
    color_map = {'planned': '#6c757d', 'in_progress': '#0d6efd', 'done': '#198754'}
    events = [{
        'title': task.title,
        'start': task.due_date.strftime('%Y-%m-%d'),
        'color': color_map.get(task.status, '#6c757d'),
        'extendedProps': {
            'status': task.get_status_display(),
            'task_id': task.id
        }
    } for task in tasks]
    return JsonResponse(events, safe=False)

@login_required
def activity_view(request):
    user = request.user
    today = now().date()
    tasks = Task.objects.filter(user=user)

    total = tasks.count()
    completed = tasks.filter(status='done').count()
    remaining = tasks.exclude(status='done').count()
    overdue = tasks.filter(status__in=['planned', 'in_progress'], due_date__lt=today).count()

    done_tasks = tasks.filter(status='done', completed_at__isnull=False)
    done_data = {}
    for task in done_tasks:
        day = task.completed_at.date()
        done_data[day] = done_data.get(day, 0) + 1

    done_labels = list(map(str, sorted(done_data)))
    done_counts = [done_data[day] for day in sorted(done_data)]

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
def update_task_status(request, pk, new_status):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.status = new_status
    task.completed = new_status == 'done'
    task.completed_at = now() if task.completed else None
    task.save()
    return HttpResponseRedirect(reverse('tasks'))

@login_required
def task_list(request):
    tasks_qs = Task.objects.filter(user=request.user)

    # --- Категория ---
    category_id = request.GET.get('category')
    selected_category = None
    if category_id and category_id != "None":
        try:
            selected_category = int(category_id)
            tasks_qs = tasks_qs.filter(categories__id=selected_category)
        except (ValueError, TypeError):
            selected_category = None

    # --- Сортировка ---
    valid_sort_fields = ['title', 'due_date', 'priority', 'created_at', 'status']
    sort = request.GET.get('sort')
    order = request.GET.get('order', 'asc')

    if sort not in valid_sort_fields:
        sort = 'title'  # дефолтное поле сортировки

    ordering = sort if order == 'asc' else f"-{sort}"
    tasks_qs = tasks_qs.order_by(ordering)

    # --- Пагинация ---
    paginator = Paginator(tasks_qs, 4)
    page_obj = paginator.get_page(request.GET.get('page'))

    # --- Категории ---
    categories = Category.objects.filter(user=request.user)

    context = {
        'tasks': page_obj,
        'categories': categories,
        'selected_category': selected_category,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'core/includes/_task_list_ajax.html', context)

    return render(request, 'core/tasks.html', context)

@login_required
def task_create(request):
    form = TaskForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        task = form.save(commit=False)
        task.user = request.user
        task.save()
        form.save_m2m()
        return redirect('tasks')
    return render(request, 'core/task_form.html', {'form': form})

@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    form = TaskForm(request.POST or None, instance=task, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('tasks')
    return render(request, 'core/task_form.html', {'form': form})

@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == 'POST':
        task.delete()
        return redirect('tasks')
    return render(request, 'core/task_confirm_delete.html', {'task': task})

def register_view(request):
    form = CustomRegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        email = user.email
        try:
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
    return render(request, 'core/register.html', {'form': form})

def home(request):
    if request.user.is_authenticated:
        user = request.user
        today = now().date()
        tasks = Task.objects.filter(user=user).order_by('-created_at')

        paginator = Paginator(tasks, 3)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        total = tasks.count()
        completed = tasks.filter(status='done').count()
        in_progress = tasks.filter(status='in_progress').count()
        planned = tasks.filter(status='planned').count()
        overdue = tasks.filter(status__in=['planned', 'in_progress'], due_date__lt=today).count()
        remaining = tasks.exclude(status='done').count()

        context = {
            'page_obj': page_obj,
            'planned': planned,
            'in_progress': in_progress,
            'completed': completed,
            'total': total,
            'remaining': remaining,
            'overdue': overdue,
        }

        # Если AJAX — вернуть только HTML задач
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            html = render_to_string('core/includes/_task_cards.html', context, request=request)
            return HttpResponse(html)

        return render(request, 'core/home.html', context)
    else:
        return render(request, 'core/home.html', {
            'page_obj': None,
            'planned': 0,
            'in_progress': 0,
            'completed': 0,
            'total': 0,
            'remaining': 0,
            'overdue': 0,
        })

@login_required
def category_list(request):
    categories = Category.objects.filter(user=request.user)
    return render(request, 'core/categories.html', {'categories': categories})

@login_required
def category_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            try:
                Category.objects.create(name=name, user=request.user)
                return redirect('category_list')
            except:
                messages.error(request, 'Категория с таким названием уже существует. Пожалуйста, выберите другое название.')
    return render(request, 'core/category_form.html')

@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    
    if request.method == 'POST':
        category.delete()
        # Проверяем, остались ли еще категории
        remaining_categories = Category.objects.filter(user=request.user).exists()
        if not remaining_categories:
            messages.info(request, 'Вы удалили последнюю категорию. Вы можете создать новую или вернуться к задачам.')
            return redirect('category_list')
        return redirect('category_list')
    
    # Проверяем, является ли это последней категорией
    is_last_category = Category.objects.filter(user=request.user).count() == 1
    
    return render(request, 'core/category_confirm_delete.html', {
        'category': category,
        'is_last_category': is_last_category
    })

@login_required
def assign_category(request, task_id):
    task = get_object_or_404(Task, pk=task_id, user=request.user)

    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        task.categories.clear()
        if category_id:
            try:
                category = Category.objects.get(id=category_id, user=request.user)
                task.categories.add(category)
            except Category.DoesNotExist:
                pass

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        return redirect('tasks')

@login_required
def home_tasks_ajax(request):
    tasks = Task.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(tasks, 3)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'core/includes/_task_cards.html', {'page_obj': page_obj})