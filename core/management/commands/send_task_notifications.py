from django.core.management.base import BaseCommand
from django.utils.timezone import now, make_aware, localtime
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from core.models import Task, CustomUser
from datetime import datetime as dt, timedelta

class Command(BaseCommand):
    help = "Send notifications about upcoming or overdue tasks"

    def handle(self, *args, **kwargs):
        now_local = localtime(now())
        today = now_local.date()
        tomorrow = today + timedelta(days=1)

        # Получаем всех пользователей, у которых включены уведомления
        users = CustomUser.objects.filter(receive_notifications=True)

        for user in users:
            # Получаем задачи пользователя
            user_tasks = Task.objects.filter(user=user)

            # Просроченные задачи
            overdue = user_tasks.filter(
                due_date__lt=today,
                status__in=['planned', 'in_progress']
            )

            # Задачи на завтра
            upcoming = user_tasks.filter(
                due_date=tomorrow,
                status__in=['planned', 'in_progress']
            )

            # Задачи в процессе
            in_progress = user_tasks.filter(
                status='in_progress'
            ).exclude(id__in=upcoming.values_list('id', flat=True))

            # Запланированные задачи
            planned = user_tasks.filter(
                status='planned',
                due_date__gt=tomorrow
            ).exclude(id__in=upcoming.values_list('id', flat=True))

            # Отправляем письмо, только если есть любые активные задачи
            if any([overdue.exists(), upcoming.exists(), in_progress.exists(), planned.exists()]):
                html_message = render_to_string('core/emails/task_notification.html', {
                    'user': user,
                    'upcoming': upcoming,
                    'overdue': overdue,
                    'in_progress': in_progress,
                    'planned': planned,
                    'site_url': 'http://127.0.0.1:8000'  # замените на прод-адрес при деплое
                })

                plain_message = strip_tags(html_message)

                try:
                    send_mail(
                        subject="📌 Обзор ваших задач — Flowvance",
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        html_message=html_message,
                        fail_silently=True,
                    )
                    self.stdout.write(f"Уведомление отправлено пользователю {user.email}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Ошибка отправки уведомления пользователю {user.email}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("Уведомления успешно отправлены."))
