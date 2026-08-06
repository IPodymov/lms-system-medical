"""Шаблонные теги для единого рендера форм.

До этого в проекте было три несовместимых способа выводить форму
({{ form.as_p }}, поля по одному, полностью ручной HTML) и ни одного стиля
ошибки поля. Эти теги дают один способ и заодно проставляют ARIA-атрибуты,
которые вручную забываются чаще всего.

Библиотека crispy-forms сюда не подходит: она улучшает только те формы,
которые уже являются Django Form, а таких в проекте меньшинство — остальные
написаны ручным HTML и читаются во view через request.POST.
"""

from django import forms, template
from django.forms import BoundField

register = template.Library()

# Виджет -> класс поля из слоя компонентов.
_WIDGET_CLASSES = (
    (forms.Textarea, "ui-textarea"),
    (forms.Select, "ui-select"),
)


def _control_class(widget: forms.Widget) -> str:
    """Подобрать класс оформления по типу виджета."""
    for widget_type, css_class in _WIDGET_CLASSES:
        if isinstance(widget, widget_type):
            return css_class
    return "ui-input"


def _is_choice(widget: forms.Widget) -> bool:
    return isinstance(widget, forms.CheckboxInput | forms.RadioSelect)


@register.inclusion_tag("components/field.html")
def form_field(
    field: BoundField,
    *,
    autofocus: bool = False,
    autocomplete: str | None = None,
    placeholder: str | None = None,
    hint: str | None = None,
) -> dict:
    """Отрисовать поле формы: метка, виджет, подсказка, ошибка.

    Поле связывается с подсказкой и ошибкой через aria-describedby, а при
    ошибке получает aria-invalid — без этого скринридер читает поле как
    обычное и не сообщает, что с ним не так.
    """
    widget = field.field.widget
    described_by = []

    hint_text = hint or field.help_text
    if hint_text:
        described_by.append(f"{field.auto_id}-hint")
    if field.errors:
        described_by.append(f"{field.auto_id}-error")

    attrs: dict[str, object] = {}
    if not _is_choice(widget):
        attrs["class"] = _control_class(widget)
    if described_by:
        attrs["aria-describedby"] = " ".join(described_by)
    if field.errors:
        attrs["aria-invalid"] = "true"
    if autofocus:
        attrs["autofocus"] = True
    if autocomplete:
        attrs["autocomplete"] = autocomplete
    if placeholder:
        attrs["placeholder"] = placeholder

    return {
        "field": field,
        "widget": field.as_widget(attrs=attrs),
        "hint": hint_text,
        "hint_id": f"{field.auto_id}-hint",
        "error_id": f"{field.auto_id}-error",
        "errors": field.errors,
        "is_choice": _is_choice(widget),
    }


@register.inclusion_tag("components/form_errors.html")
def form_errors(form: forms.BaseForm, title: str = "Проверьте форму") -> dict:
    """Сводка ошибок формы по образцу GOV.UK.

    Ставится в начало страницы, выше <h1>. Каждый пункт — ссылка на поле,
    текст пункта обязан дословно совпадать с текстом ошибки у поля, иначе
    пользователь не свяжет их между собой.

    Ошибки, не привязанные к полю, идут первыми и без ссылки: вести по ним
    некуда.
    """
    if not form.is_bound or form.is_valid():
        return {"errors": [], "title": title}

    errors = [{"message": message, "anchor": None} for message in form.non_field_errors()]
    for field in form:
        errors += [{"message": message, "anchor": field.auto_id} for message in field.errors]
    return {"errors": errors, "title": title}
