"""Запросы на чтение для записей на курс."""

from django.db.models import Count, Q, QuerySet

# Условия «блок считается в прогрессе» продублированы из
# services.recalculate_course_progress намеренно: там они применяются к
# ContentBlock напрямую, здесь — через два разных пути связей от Enrollment.
# Если правило изменится, править нужно оба места, поэтому оно вынесено в
# именованные константы, а не разбросано по фильтрам.
_PUBLISHED_AND_REQUIRED = {
    "course_run__course__sections__is_published": True,
    "course_run__course__sections__lessons__is_published": True,
    "course_run__course__sections__lessons__blocks__is_required": True,
}

_COMPLETED_AND_COUNTED = {
    "progresses__status": "completed",
    "progresses__content_block__is_required": True,
    "progresses__content_block__lesson__is_published": True,
    "progresses__content_block__lesson__section__is_published": True,
}


def with_block_counts(enrollments: QuerySet) -> QuerySet:
    """Добавить счётчики блоков: сколько всего и сколько пройдено.

    Одного `progress_percent` карточке курса недостаточно: «43%» не отвечает
    на вопрос «сколько мне осталось», а «7 из 16» отвечает. Считается двумя
    аннотациями, а не запросом на запись, поэтому список остаётся одним
    запросом к базе независимо от числа записей.

    `distinct=True` обязателен: обе аннотации идут по разным путям связей, и
    без него строки перемножаются на соединении.
    """
    return enrollments.annotate(
        blocks_total=Count(
            "course_run__course__sections__lessons__blocks",
            filter=Q(**_PUBLISHED_AND_REQUIRED),
            distinct=True,
        ),
        blocks_done=Count(
            "progresses",
            filter=Q(**_COMPLETED_AND_COUNTED),
            distinct=True,
        ),
    )
