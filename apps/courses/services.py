from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.assessments.models import Question, QuestionOption, Quiz, QuizQuestion

from .models import (
    ContentBlock,
    CourseRun,
    CourseRunStaff,
    CourseSection,
    FileContent,
    Lesson,
    TextContent,
)


def create_course_run(course, user, *, start_at, end_at, status):
    run = CourseRun.objects.create(
        course=course,
        title=f"{course.title} — основной поток",
        semester="Открытый",
        academic_year=f"{start_at.year}/{start_at.year + 1}",
        start_at=start_at,
        end_at=end_at,
        enrollment_start_at=timezone.now(),
        enrollment_end_at=end_at,
        status=status,
    )
    CourseRunStaff.objects.get_or_create(
        course_run=run,
        user=user,
        defaults={"role": "teacher"},
    )
    return run


def ensure_active_course_run(course, user):
    """Create or activate one immediately available run when a course is first published."""
    active_run = course.runs.filter(status=CourseRun.Status.ACTIVE).first()
    if active_run:
        return active_run
    now = timezone.now()
    run = course.runs.filter(status=CourseRun.Status.PLANNED).order_by("created_at").first()
    if run:
        run.status = CourseRun.Status.ACTIVE
        run.enrollment_start_at = min(run.enrollment_start_at, now)
        run.enrollment_end_at = max(run.enrollment_end_at, now)
        run.save(update_fields=["status", "enrollment_start_at", "enrollment_end_at"])
        CourseRunStaff.objects.get_or_create(
            course_run=run, user=user, defaults={"role": "teacher"}
        )
        return run
    return create_course_run(
        course,
        user,
        start_at=now,
        end_at=now + timedelta(days=365),
        status=CourseRun.Status.ACTIVE,
    )


def add_lesson(course, *, section_title, lesson_title, description=""):
    section = course.sections.filter(title=section_title).first()
    if not section:
        section = CourseSection.objects.create(
            course=course,
            title=section_title,
            position=course.sections.count() + 1,
            is_published=True,
        )
    return Lesson.objects.create(
        section=section,
        title=lesson_title,
        description=description,
        position=section.lessons.count() + 1,
        is_published=True,
    )


def create_text_block(lesson, *, title, body):
    block = ContentBlock.objects.create(
        lesson=lesson,
        type=ContentBlock.Type.TEXT,
        title=title,
        position=lesson.blocks.count() + 1,
    )
    TextContent.objects.create(content_block=block, body=body)
    return block


def create_file_block(lesson, *, title, file, description=""):
    block = ContentBlock.objects.create(
        lesson=lesson,
        type=ContentBlock.Type.FILE,
        title=title,
        position=lesson.blocks.count() + 1,
    )
    FileContent.objects.create(content_block=block, file=file, description=description)
    return block


@transaction.atomic
def create_quiz_block(
    lesson,
    *,
    title,
    question_text,
    options,
    correct_indexes,
    organization,
    author,
    question_type=Question.Type.SINGLE,
    image=None,
    markers=None,
):
    """Create a quiz content block with a single question and its options.

    `markers` (if given) is a list of (x, y) percent-coordinates aligned with `options`,
    used for image-based questions.
    """
    block = ContentBlock.objects.create(
        lesson=lesson,
        type=ContentBlock.Type.QUIZ,
        title=title,
        position=lesson.blocks.count() + 1,
    )
    quiz = Quiz.objects.create(content_block=block, title=title, passing_score=100)
    question = Question.objects.create(
        organization=organization,
        author=author,
        type=question_type,
        text=question_text,
        image=image,
    )
    for position, option in enumerate(options, start=1):
        marker = markers[position - 1] if markers else None
        QuestionOption.objects.create(
            question=question,
            text=option,
            position=position,
            marker_x=marker[0] if marker else None,
            marker_y=marker[1] if marker else None,
            is_correct=position - 1 in correct_indexes,
        )
    QuizQuestion.objects.create(quiz=quiz, question=question, position=1)
    return block


def renumber_positions(ordered_queryset) -> None:
    """Reassign consecutive `position` values to match `ordered_queryset`'s current order."""
    for position, item in enumerate(ordered_queryset, start=1):
        if item.position != position:
            item.position = position
            item.save(update_fields=["position"])


def reorder(items: dict, ordered_ids: list) -> None:
    """Reassign `position` 1..N to match `ordered_ids`, for the given {id: instance} map.

    Positions are first moved out of range to avoid a transient unique-constraint clash
    when two neighbouring items are swapped.
    """
    offset = len(ordered_ids) + 1000
    for item in items.values():
        item.position += offset
        item.save(update_fields=["position"])
    for position, item_id in enumerate(ordered_ids, start=1):
        item = items.get(item_id)
        if item:
            item.position = position
            item.save(update_fields=["position"])
