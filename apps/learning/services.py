from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.courses.models import ContentBlock, CourseRun

from .models import ContentProgress, Enrollment


class EnrollmentError(ValueError):
    pass


@transaction.atomic
def enroll(*, course_run: CourseRun, user, source: str = "self") -> Enrollment:
    run = CourseRun.objects.select_for_update().get(pk=course_run.pk)
    now = timezone.now()
    if run.status != CourseRun.Status.ACTIVE:
        raise EnrollmentError("Запись доступна только на активный поток.")
    if not run.enrollment_start_at <= now <= run.enrollment_end_at:
        raise EnrollmentError("Период записи на курс завершён.")
    if (
        run.max_students
        and Enrollment.objects.filter(
            course_run=run, status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.INVITED]
        ).count()
        >= run.max_students
    ):
        raise EnrollmentError("Поток заполнен.")
    try:
        enrollment, created = Enrollment.objects.get_or_create(
            course_run=run, user=user, defaults={"enrollment_source": source}
        )
    except IntegrityError:
        enrollment = Enrollment.objects.get(course_run=run, user=user)
        created = False
    if created:
        from apps.notifications.tasks import create_notification

        transaction.on_commit(
            lambda: create_notification.delay(
                str(user.pk), "enrollment", "Вы записаны на курс", run.title
            )
        )
    return enrollment


@transaction.atomic
def update_progress(
    *, enrollment: Enrollment, block: ContentBlock, percent: Decimal = Decimal("100")
) -> ContentProgress:
    progress, _ = ContentProgress.objects.select_for_update().get_or_create(
        enrollment=enrollment, content_block=block
    )
    progress.progress_percent = percent
    progress.status = "completed" if percent >= 100 else "in_progress"
    progress.started_at = progress.started_at or timezone.now()
    progress.completed_at = timezone.now() if progress.status == "completed" else None
    progress.save()
    recalculate_course_progress(enrollment)
    return progress


def recalculate_course_progress(enrollment: Enrollment) -> None:
    required = ContentBlock.objects.filter(
        lesson__section__course=enrollment.course_run.course,
        is_required=True,
        lesson__is_published=True,
        lesson__section__is_published=True,
    )
    total = required.count()
    completed = ContentProgress.objects.filter(
        enrollment=enrollment, content_block__in=required, status="completed"
    ).values_list("content_block_id", flat=True)
    partial = (
        ContentProgress.objects.filter(enrollment=enrollment, content_block__in=required)
        .exclude(status="completed")
        .values_list("progress_percent", flat=True)
    )
    value = Decimal(len(completed)) * Decimal("100") + sum(
        (Decimal(item) for item in partial), Decimal("0")
    )
    enrollment.progress_percent = (
        Decimal("0") if not total else (value / Decimal(total)).quantize(Decimal(".01"))
    )
    enrollment.save(update_fields=["progress_percent", "updated_at"])
