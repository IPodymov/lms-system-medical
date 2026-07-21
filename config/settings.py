import os
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent.parent
# Process variables always take priority. Vercel receives its production settings
# directly through the platform environment.
ENVIRONMENT = os.getenv("DJANGO_ENV", "production" if os.getenv("VERCEL") else "local")
ENVIRONMENT_FILE = ".env.production" if ENVIRONMENT == "production" else ".env"
environment_values = dict(dotenv_values(BASE_DIR / ENVIRONMENT_FILE))
for key, value in environment_values.items():
    if value is not None:
        os.environ.setdefault(key, value)


def database_config(url: str) -> dict[str, Any]:
    """Build Django's PostgreSQL configuration from a standard database URL."""
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL must use the postgres:// or postgresql:// scheme.")
    if not parsed.hostname or not parsed.path or not parsed.username:
        raise ValueError("DATABASE_URL must include host, database name, and user.")

    query = parse_qs(parsed.query)
    options = {key: query[key][-1] for key in ("sslmode", "connect_timeout") if query.get(key)}
    config: dict[str, Any] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname,
        "PORT": str(parsed.port or 5432),
    }
    if options:
        config["OPTIONS"] = options
    return config


IS_VERCEL = bool(os.getenv("VERCEL"))
IS_DEPLOYMENT = ENVIRONMENT == "production"
_configured_secret_key = os.getenv("DJANGO_SECRET_KEY")
if IS_DEPLOYMENT and not _configured_secret_key:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY is required on deployed environments.")
SECRET_KEY = _configured_secret_key or "unsafe-local-development-key"
DEBUG = os.getenv("DEBUG", "1") == "1" and not IS_DEPLOYMENT
_configured_admin_url = os.getenv("DJANGO_ADMIN_URL", "").strip("/")
# Keep the familiar URL during local development. On Vercel, the admin is
# deliberately unavailable until a private URL is configured.
ADMIN_URL = "admin/" if DEBUG else f"{_configured_admin_url}/" if _configured_admin_url else ""
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
if vercel_domain := os.getenv("VERCEL_URL"):
    ALLOWED_HOSTS.append(vercel_domain)
ALLOWED_HOSTS = list(dict.fromkeys(host.strip() for host in ALLOWED_HOSTS if host.strip()))

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()
]
if vercel_domain:
    CSRF_TRUSTED_ORIGINS.append(f"https://{vercel_domain}")
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS))
INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "drf_spectacular",
    "django_htmx",
    "apps.accounts",
    "apps.organizations",
    "apps.courses",
    "apps.learning",
    "apps.assessments",
    "apps.grading",
    "apps.notifications",
    "apps.messaging",
    "apps.audit",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.static_asset_version",
                "config.context_processors.navigation_context",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
if os.getenv("DJANGO_USE_SQLITE") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
elif database_url := os.getenv("DATABASE_URL"):
    DATABASES = {"default": database_config(database_url)}
elif IS_VERCEL:
    raise ImproperlyConfigured("DATABASE_URL is required for Vercel deployments.")
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
# Local development storage: course files are saved in <project root>/media/.
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
WHITENOISE_MANIFEST_STRICT = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG and os.getenv("DJANGO_USE_SQLITE") != "1":
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31_536_000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
SPECTACULAR_SETTINGS = {"TITLE": "University LMS API", "VERSION": "0.1.0"}
# Redis is shared by Celery, the cache and the Channels layer in Docker. Local
# development and tests stay usable without a running Redis instance.
CACHE_URL = os.getenv("CACHE_URL", "")
USE_IN_MEMORY_SERVICES = os.getenv("DJANGO_USE_SQLITE") == "1"
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "cache+memory://" if USE_IN_MEMORY_SERVICES else CELERY_BROKER_URL
# A local SQLite setup has no Redis worker. Vercel has no worker either, so
# both environments execute short notification tasks within the request.
CELERY_TASK_ALWAYS_EAGER = USE_IN_MEMORY_SERVICES or IS_VERCEL
CELERY_TASK_EAGER_PROPAGATES = CELERY_TASK_ALWAYS_EAGER
CELERY_TASK_STORE_EAGER_RESULT = False
if CACHE_URL and not USE_IN_MEMORY_SERVICES:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": CACHE_URL,
            "TIMEOUT": 300,
            "OPTIONS": {"socket_connect_timeout": 1, "socket_timeout": 1},
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "medical-lms-local",
            "TIMEOUT": 300,
        }
    }

CHANNEL_REDIS_URL = "" if USE_IN_MEMORY_SERVICES else os.getenv("CHANNEL_REDIS_URL", CACHE_URL)
if CHANNEL_REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [CHANNEL_REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
