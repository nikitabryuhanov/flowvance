# Flowvance

Flowvance - это веб-приложение для управления задачами, разработанное на Django. Оно помогает пользователям организовывать свои задачи, отслеживать прогресс и повышать продуктивность.

## Основные функции

- Создание и управление задачами
- Категоризация задач
- Отслеживание статуса выполнения
- Календарь задач
- Статистика и аналитика
- Уведомления
- Профиль пользователя с настройками

## Технологии

- Python 3.x
- Django
- Bootstrap 5
- Chart.js
- FullCalendar

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/ваш-username/flowvance.git
cd flowvance
```

2. Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Примените миграции:
```bash
python manage.py migrate
```

5. Создайте суперпользователя:
```bash
python manage.py createsuperuser
```

6. Запустите сервер разработки:
```bash
python manage.py runserver
```

## Использование

1. Откройте браузер и перейдите по адресу `http://localhost:8000`
2. Зарегистрируйтесь или войдите в систему
3. Начните создавать и управлять своими задачами

## Лицензия

MIT