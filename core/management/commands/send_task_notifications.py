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

        start = make_aware(dt.combine(tomorrow, dt.min.time()))
        end = make_aware(dt.combine(tomorrow, dt.max.time()))

        users = CustomUser.objects.filter(receive_notifications=True)

        for user in users:
            # Получаем все активные задачи пользователя
            all_tasks = Task.objects.filter(
                user=user,
                status__in=['planned', 'in_progress']
            ).order_by('due_date')

            # Разделяем задачи на категории
            upcoming = all_tasks.filter(due_date__range=(start, end))
            overdue = all_tasks.filter(due_date__lt=now_local)
            in_progress = all_tasks.filter(status='in_progress')
            planned = all_tasks.filter(status='planned')

            if all_tasks.exists():
                html_message = render_to_string('core/emails/task_notification.html', {
                    'user': user,
                    'upcoming': upcoming,
                    'overdue': overdue,
                    'in_progress': in_progress,
                    'planned': planned,
                    'site_url': 'http://127.0.0.1:8000'  # замените на прод-адрес при деплое
                })

                plain_message = strip_tags(html_message)

                send_mail(
                    subject="📌 Обзор ваших задач — Flowvance",
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=True,
                )

        self.stdout.write(self.style.SUCCESS("Уведомления успешно отправлены."))
