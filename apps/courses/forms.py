"""Формы создания курса и теста.

До этапа 4.11 обе формы читались во view из `request.POST`, а введённое
возвращалось в разметку через `{{ request.POST.title }}` прямо в шаблоне.
Работало это только для полей, которые кто-то не забыл так вернуть, и не
давало ни одной ошибки у поля: единственным ответом был `messages.error`
поверх страницы.
"""

from datetime import datetime, time

from django import forms
from django.utils import timezone

from apps.courses.models import Course, Lesson

# Число вариантов ответа в форме теста. Столько же полей рисует шаблон.
QUIZ_OPTION_COUNT = 4


class CourseCreateForm(forms.ModelForm):
    course_start = forms.DateField(
        label="Дата начала", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    course_end = forms.DateField(
        label="Дата окончания", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = Course
        fields = ["title", "short_description", "description", "cover"]
        labels = {
            "title": "Наименование курса",
            "short_description": "Краткое описание",
            "description": "Подробное описание",
            "cover": "Обложка",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 6})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].error_messages["required"] = "Укажите наименование курса."

    def clean(self) -> dict:
        cleaned_data = super().clean()
        start = cleaned_data.get("course_start")
        end = cleaned_data.get("course_end")
        # Сроки необязательны, но задаются только парой: поток без даты
        # окончания в расписании неотличим от бессрочного.
        if bool(start) != bool(end):
            self.add_error(
                "course_end" if start else "course_start",
                "Укажите и дату начала, и дату окончания обучения.",
            )
        elif start and end and end <= start:
            self.add_error("course_end", "Дата окончания обучения должна быть позже даты начала.")
        return cleaned_data

    def course_run_period(self) -> tuple[datetime | None, datetime | None]:
        """Границы первого потока: начало дня старта и конец дня финиша."""
        start = self.cleaned_data.get("course_start")
        end = self.cleaned_data.get("course_end")
        if not start or not end:
            return None, None
        return (
            timezone.make_aware(datetime.combine(start, time.min)),
            timezone.make_aware(datetime.combine(end, time.max)),
        )


class QuizCreateForm(forms.Form):
    """Вопрос теста: текстовые варианты или отметки на изображении.

    Варианты и отметки приходят списками одноимённых полей, поэтому
    разбираются в clean(), а не описываются отдельными полями формы. Раньше
    тот же разбор жил во view вперемешку с созданием объектов.
    """

    # Тема необязательна: без выбора блок уходит в первую тему курса, а
    # если программы ещё нет — она создаётся. Так работало и до формы.
    lesson = forms.ModelChoiceField(queryset=Lesson.objects.none(), label="Тема", required=False)
    quiz_title = forms.CharField(label="Название теста", max_length=255)
    question_text = forms.CharField(label="Вопрос", widget=forms.Textarea(attrs={"rows": 4}))
    question_kind = forms.ChoiceField(
        label="Тип вопроса",
        choices=[("text", "Варианты текста"), ("image", "Отметки на изображении")],
        initial="text",
        # Не required: прежний код принимал POST без этих полей и считал
        # вопрос текстовым с одним ответом. Интерфейс их всегда шлёт,
        # но ломать существующий контракт формы ради строгости незачем.
        required=False,
        widget=forms.RadioSelect,
    )
    answer_mode = forms.ChoiceField(
        label="Сколько правильных ответов?",
        choices=[
            ("single", "Один правильный ответ"),
            ("multiple", "Несколько правильных ответов"),
        ],
        initial="single",
        required=False,
    )
    # FileField, а не ImageField: проверка Pillow отвергает файлы, которые
    # прежний код принимал, и это была бы не миграция вёрстки, а смена
    # правил приёма. Решение о проверке содержимого — отдельный разговор.
    question_image = forms.FileField(label="Изображение", required=False)

    @property
    def option_indexes(self) -> range:
        """Номера полей вариантов ответа — чтобы шаблон не хардкодил их число."""
        return range(QUIZ_OPTION_COUNT)

    def __init__(self, *args, lessons=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lesson"].queryset = lessons
        self.fields["lesson"].label_from_instance = lambda lesson: (
            f"{lesson.section.title} | {lesson.title}"
        )

    @property
    def is_image_question(self) -> bool:
        return (self.data.get("question_kind") or self.fields["question_kind"].initial) == "image"

    def _markers(self) -> list[tuple[float, float]]:
        xs = self.data.getlist("marker_x")
        ys = self.data.getlist("marker_y")
        if len(xs) != len(ys):
            return []
        markers = []
        for x, y in zip(xs, ys, strict=True):
            try:
                marker_x, marker_y = float(x), float(y)
            except ValueError:
                return []
            if not 0 <= marker_x <= 100 or not 0 <= marker_y <= 100:
                return []
            markers.append((marker_x, marker_y))
        return markers

    def _correct_indexes(self) -> set[int]:
        try:
            return {int(value) for value in self.data.getlist("correct_option")}
        except ValueError:
            return set()

    def clean(self) -> dict:
        cleaned_data = super().clean()
        cleaned_data["question_kind"] = cleaned_data.get("question_kind") or "text"
        cleaned_data["answer_mode"] = cleaned_data.get("answer_mode") or "single"
        markers = self._markers() if self.is_image_question else []
        if self.is_image_question:
            options = [f"Область {position}" for position in range(1, len(markers) + 1)]
        else:
            options = [value.strip() for value in self.data.getlist("option") if value.strip()]
        correct_indexes = self._correct_indexes()

        minimum_options = 1 if self.is_image_question else 2
        question_type_is_multiple = cleaned_data.get("answer_mode") == "multiple"
        enough_correct = (
            len(correct_indexes) >= 1
            and correct_indexes.issubset(range(len(options)))
            and (question_type_is_multiple or len(correct_indexes) == 1)
        )

        # Формулировка сохранена дословно: варианты и отметки — не поля
        # формы, привязать сообщение к конкретному полю не к чему.
        if len(options) < minimum_options or not enough_correct:
            raise forms.ValidationError(
                "Заполните вопрос, добавьте области на изображение и отметьте правильные ответы."
            )
        if self.is_image_question and not cleaned_data.get("question_image"):
            self.add_error("question_image", "Загрузите изображение для вопроса.")

        cleaned_data["options"] = options
        cleaned_data["correct_indexes"] = correct_indexes
        cleaned_data["markers"] = markers
        return cleaned_data
