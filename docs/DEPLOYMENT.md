# Развёртывание

Для production задайте уникальный `DJANGO_SECRET_KEY`, `DEBUG=0`, список `ALLOWED_HOSTS`, безопасные PostgreSQL-пароли и внешнее хранилище медиа. Перед запуском выполните миграции и collectstatic.
