from django.apps import AppConfig


class UiConfig(AppConfig):
    """Общие шаблонные теги и партиалы интерфейса.

    Приложение намеренно без моделей, view и URL: у переиспользуемых
    шаблонных тегов должен быть дом, а Django ищет templatetags только
    внутри установленных приложений. Логики предметной области здесь нет.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ui"
    verbose_name = "Интерфейс"
