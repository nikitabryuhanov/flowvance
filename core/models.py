from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    receive_notifications = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    class Meta:
        db_table = 'core_customuser'

class Category(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['name', 'user']

    def __str__(self):
        return self.name

class Task(models.Model):
    PRIORITY_CHOICES = [
        ('1', 'Низкий'),
        ('2', 'Средний'),
        ('3', 'Высокий'),
    ]

    STATUS_CHOICES = [
        ('planned', 'Запланировано'),
        ('in_progress', 'В процессе'),
        ('done', 'Выполнено'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(verbose_name="Дедлайн", null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=1, choices=PRIORITY_CHOICES, default='2')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planned'
    )
    completed = models.BooleanField(default=False)
    categories = models.ManyToManyField(Category, blank=True)

    def __str__(self):
        return self.title

class PasswordResetCode(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Код {self.code} для {self.user.email}"

class EmailChangeCode(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    new_email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} -> {self.new_email}"
