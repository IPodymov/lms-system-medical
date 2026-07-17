# Деплой на Vercel

Проект использует нативное распознавание Django на Vercel. Достаточно импортировать репозиторий в Vercel или выполнить `vercel` из корня проекта; `vercel.json` фиксирует фреймворк.

## Обязательные переменные окружения

Добавьте для Production и Preview:

- `DJANGO_SECRET_KEY` — новый случайный секрет, уникальный для окружения;
- `DATABASE_URL` — URL внешней PostgreSQL-базы с TLS, например Neon или Vercel Marketplace;
- `ALLOWED_HOSTS` — `.vercel.app` и собственный домен, если он есть;
- `CSRF_TRUSTED_ORIGINS` — `https://*.vercel.app` и URL собственного домена;
- `DJANGO_ADMIN_URL` — приватный путь к админке без начального слеша.

`VERCEL_URL` добавляется Vercel автоматически и также включается приложением в допустимые домены и CSRF origins. В production `DJANGO_SECRET_KEY` обязателен: приложение не запустится с локальным небезопасным значением.

## База данных и миграции

Vercel Functions не предоставляют постоянную файловую БД. Подключите PostgreSQL через `DATABASE_URL`, затем перед promotion production-версии выполните миграции из CI или локальной машины с теми же переменными:

```bash
python manage.py migrate
vercel deploy --prod
```

## Ограничения serverless-среды

- Celery-воркер на Vercel не запускается. Короткие задачи в Vercel выполняются синхронно через eager-режим; для очередей и длительных задач оставьте отдельный worker/Redis вне Vercel.
- Локальная директория `media/` эфемерна. Для загружаемых обложек и материалов подключите постоянное object storage до production-использования этой функции.

## Проверка

Перед деплоем выполните:

```bash
python manage.py check
python manage.py test
ruff check .
ruff format --check .
```
