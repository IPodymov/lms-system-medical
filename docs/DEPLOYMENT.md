# Развёртывание

Для production задайте уникальный `DJANGO_SECRET_KEY`, `DEBUG=0`, список `ALLOWED_HOSTS`, безопасные PostgreSQL-пароли и внешнее хранилище медиа. Перед запуском выполните миграции и collectstatic.

## Доступ к Django admin

При `DEBUG=1` Django admin доступна суперпользователю по адресу `/admin/`.

В Vercel production маршрут админки по умолчанию отключён. Чтобы включить его, добавьте в Vercel Environment Variables `DJANGO_ADMIN_URL` с длинным непубличным значением без начального слеша, например `control-4f6d8a92`. Тогда суперпользователь сможет войти по адресу:

`https://<YOUR_VERCEL_DOMAIN>/control-4f6d8a92/`

Не публикуйте эту ссылку и не используйте значение `admin`.

Инструкции для Vercel, включая подключение PostgreSQL через `DATABASE_URL`, находятся в [VERCEL.md](VERCEL.md).
