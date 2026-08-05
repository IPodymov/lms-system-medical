# Развёртывание

Для production задайте уникальный `DJANGO_SECRET_KEY`, `DEBUG=0`, список `ALLOWED_HOSTS`, безопасные PostgreSQL-пароли и внешнее хранилище медиа. Перед запуском выполните миграции и collectstatic.

## Доступ к Django admin

При `DEBUG=1` Django admin доступна суперпользователю по адресу `/admin/`.

В Vercel production маршрут админки по умолчанию отключён. Чтобы включить его, добавьте в Vercel Environment Variables `DJANGO_ADMIN_URL` с длинным непубличным значением без начального слеша, например `control-4f6d8a92`. Тогда суперпользователь сможет войти по адресу:

`https://<YOUR_VERCEL_DOMAIN>/control-4f6d8a92/`

Не публикуйте эту ссылку и не используйте значение `admin`.

Инструкции для Vercel, включая подключение PostgreSQL через `DATABASE_URL`, находятся в [VERCEL.md](VERCEL.md).

## CI/CD

`.github/workflows/ci.yml` на каждый push в `main` и на каждый pull request прогоняет `ruff check`, `ruff format --check`, `pylint`, `python manage.py check`, проверку отсутствующих миграций и полный набор тестов. Прогон идёт на SQLite с `DJANGO_USE_SQLITE=1` (тот же быстрый режим, что уже использует `Dockerfile` на шаге сборки) — реальная production-база на Railway/Vercel при этом не используется и не может быть задета.

Деплой выполняет сама Vercel через нативную Git-интеграцию: production-деплой при push в `main`, preview-деплой на каждый pull request — отдельный workflow для этого не нужен.

Чтобы деплой в `main` происходил только после успешного прохождения CI (если ветка `main` защищена и изменения попадают через pull request), включите в GitHub required status check:

1. Settings → Branches → правило защиты для `main`.
2. Отметьте «Require status checks to pass before merging» и выберите job `test` из workflow `CI`.

Если в `main` пушат напрямую, а не через PR, этот required-check не остановит сам push — только смержить PR без прошедшего CI будет нельзя.
