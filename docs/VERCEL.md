# Деплой на Vercel

Проект использует нативное распознавание Django на Vercel. Достаточно импортировать репозиторий в Vercel или выполнить `vercel` из корня проекта; `vercel.json` фиксирует фреймворк.

## Обязательные переменные окружения

Добавьте для Production и Preview те же значения, что подготовлены в локальном
`.env` (сам файл Vercel при Git-деплое не читает):

- `DJANGO_SECRET_KEY` — новый случайный секрет, уникальный для окружения;
- `DATABASE_URL` — URL внешней PostgreSQL-базы с TLS;
- `ALLOWED_HOSTS` — `.vercel.app` и собственный домен, если он есть;
- `CSRF_TRUSTED_ORIGINS` — `https://*.vercel.app` и URL собственного домена;
- `DJANGO_ADMIN_URL` — приватный путь к админке без начального слеша.

`DATABASE_URL` оставьте без изменений: это текущая внешняя PostgreSQL-база.
Не включайте `CELERY_BROKER_URL` в Vercel: задачи там выполняются синхронно,
а Redis-адрес из локальной сети Vercel недоступен.

`VERCEL_URL` добавляется Vercel автоматически и также включается приложением в допустимые домены и CSRF origins. В production `DJANGO_SECRET_KEY` обязателен: приложение не запустится с локальным небезопасным значением.

## Локальная синхронизация

Локальный файл `.env.local` уже добавлен в `.gitignore` и содержит безопасные параметры разработки. После связывания папки с Vercel синхронизируйте переменные нужного окружения:

```bash
vercel link
vercel env pull .env.local --environment=development --yes
```

Django читает `.env.local` только локально и не использует этот файл на Vercel.
Файлы `.env` и `.env.local` намеренно исключены из Git. Не добавляйте в Git
`DJANGO_SECRET_KEY`, `DATABASE_URL` или другие секреты.

## База данных и миграции

Vercel Functions не предоставляют постоянную файловую БД. Подключите внешнюю PostgreSQL-базу через `DATABASE_URL`, затем перед promotion production-версии выполните миграции из CI или локальной машины с теми же переменными:

```bash
python manage.py migrate
vercel deploy --prod
```

## Ограничения serverless-среды

- Celery-воркер на Vercel не запускается. Короткие задачи в Vercel выполняются синхронно через eager-режим; для очередей и длительных задач используйте отдельный worker/Redis вне Vercel.
- Локальная директория `media/` эфемерна. Для загружаемых обложек и материалов подключите постоянное object storage до production-использования этой функции.

## Проверка

Перед деплоем выполните:

```bash
python manage.py check
python manage.py test
ruff check .
ruff format --check .
```
