# МедЛМС

Локальный MVP LMS для университета: Django SSR-интерфейс, REST API, PostgreSQL/Redis/Celery в Docker.

## Быстрый старт

```bash
cp .env.example .env
docker compose up --build
# в отдельном терминале
docker compose exec web python manage.py seed_demo
```

Локально без Docker: `.venv/bin/python manage.py migrate && .venv/bin/python manage.py seed_demo && .venv/bin/python manage.py runserver`.

Приложение: http://localhost:8000, admin: http://localhost:8000/admin/, API-документация: http://localhost:8000/api/docs/.

Demo-пользователи: `admin@demo.local`, `teacher@demo.local`, `student1@demo.local`, `student2@demo.local`; пароль: `demo12345`.

Проверки: `.venv/bin/python manage.py test`, `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`.

## Проверка стиля

После установки зависимостей доступны единые команды:

```bash
ruff check .          # линтер
ruff format --check . # проверка форматирования
ruff check . --fix && ruff format . # исправить автоматически
```

Чтобы запускать их перед каждым коммитом: `pre-commit install`.
