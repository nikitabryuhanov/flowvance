from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Task, Category
from django.core.exceptions import ValidationError
from .models import CustomUser
from django.utils import timezone

class RegisterForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'priority', 'status', 'categories']
        labels = {
            'title': 'Название',
            'description': 'Описание',
            'due_date': 'Дедлайн',
            'priority': 'Приоритет',
            'status': 'Статус',
            'categories': 'Категории'
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'step': '60',
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'categories': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            categories = Category.objects.filter(user=user)
            if categories.exists():
                self.fields['categories'].queryset = categories
            else:
                self.fields.pop('categories')

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title:
            raise ValidationError('Название не может быть пустым')
        if len(title) < 3:
            raise ValidationError('Название должно содержать минимум 3 символа')
        return title

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description) > 1000:
            raise ValidationError('Описание не может быть длиннее 1000 символов')
        return description

    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now():
            raise ValidationError('Дедлайн не может быть в прошлом')
        return due_date

class CustomRegisterForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Логин'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Почта'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Повторите пароль'}),
        }

        def clean_email(self):
            email = self.cleaned_data.get('email').lower()
            if CustomUser.objects.filter(email=email).exists():
                raise ValidationError("Этот email уже зарегистрирован.")
            return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = ''

class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'avatar', 'receive_notifications']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }