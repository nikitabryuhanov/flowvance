from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.core.mail import send_mail
from django.conf import settings
from core.models import Task, CustomUser
from datetime import timedelta

class Command(BaseCommand):
    help = 'Отправка напоминаний о задачах с дедлайном сегодня или завтра'

    def handle(self, *args, **kwargs):
        today = now().date()
        tomorrow = today + timedelta(days=1)

        for user in CustomUser.objects.filter(receive_notifications=True):
            tasks = Task.objects.filter(
                user=user,
                status__in=['planned', 'in_progress'],
                due_date__in=[today, tomorrow]
            )

            if tasks.exists() and user.email:
                task_list = "\n".join([
                    f"- {task.title} (до {task.due_date})" for task in tasks
                ])

                message = (
                    f"Привет, {user.username}!\n\n"
                    f"У вас есть задачи на сегодня/завтра:\n\n{task_list}\n\n"
                    f"Не забудьте их выполнить 😊\n\n"
                    f"-- Flowvance"
                )

                send_mail(
                    subject='📝 Напоминание о задачах',
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )

        self.stdout.write(self.style.SUCCESS("Напоминания успешно отправлены!"))
