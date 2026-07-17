from django.conf import settings
from django.db import models

from apps.accounts.models import TimeStampedModel, UUIDModel
from apps.courses.models import ContentBlock, CourseRun


class Enrollment(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        INVITED = "invited", "Приглашён"
        ACTIVE = "active", "Активен"
        COMPLETED = "completed", "Завершён"
        EXPELLED = "expelled", "Отчислен"

    course_run = models.ForeignKey(CourseRun, on_delete=models.CASCADE, related_name="enrollments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    status = models.CharField(max_length=12, choices=Status, default=Status.ACTIVE)
    enrollment_source = models.CharField(
        max_length=12,
        choices=[("manual", "Вручную"), ("self", "Самозапись"), ("group", "Группа")],
        default="self",
    )
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    final_score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course_run", "user"], name="unique_enrollment")
        ]
        indexes = [
            models.Index(fields=["course_run", "status"]),
            models.Index(fields=["user", "status"]),
        ]


class ContentProgress(TimeStampedModel):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="progresses")
    content_block = models.ForeignKey(ContentBlock, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=12,
        choices=[
            ("not_started", "Не начат"),
            ("in_progress", "В процессе"),
            ("completed", "Завершён"),
        ],
        default="not_started",
    )
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_position = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "content_block"], name="unique_block_progress"
            )
        ]
        indexes = [models.Index(fields=["enrollment", "status"])]
