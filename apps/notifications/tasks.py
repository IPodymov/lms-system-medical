from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.learning.models import Enrollment

from .models import Notification


@shared_task
def create_notification(user_id: str, notification_type: str, title: str, body: str) -> None:
    Notification.objects.create(user_id=user_id, type=notification_type, title=title, body=body)


@shared_task
def remind_inactive_learners(days: int = 7) -> int:
    """Create at most one weekly reminder for learners with unfinished courses."""
    cutoff = timezone.now() - timedelta(days=days)
    enrollments = Enrollment.objects.filter(
        status="active", progress_percent__lt=100
    ).select_related("course_run__course")
    created = 0
    for enrollment in enrollments:
        if enrollment.updated_at > cutoff:
            continue
        reminder_key = f"course-reminder:{enrollment.pk}:{timezone.localdate().isoformat()}"
        if Notification.objects.filter(
            user=enrollment.user, payload__reminder_key=reminder_key
        ).exists():
            continue
        Notification.objects.create(
            user=enrollment.user,
            type="course_reminder",
            title="Пора продолжить обучение",
            body=(
                f"Вернитесь к курсу «{enrollment.course_run.course.title}». "
                f"Ваш прогресс: {enrollment.progress_percent}%."
            ),
            payload={"reminder_key": reminder_key, "enrollment_id": str(enrollment.pk)},
        )
        created += 1
    return created
