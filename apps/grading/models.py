from django.conf import settings
from django.db import models

from apps.accounts.models import TimeStampedModel, UUIDModel
from apps.courses.models import CourseRun
from apps.learning.models import Enrollment


class GradebookItem(UUIDModel, TimeStampedModel):
    course_run = models.ForeignKey(
        CourseRun, on_delete=models.CASCADE, related_name="gradebook_items"
    )
    source_type = models.CharField(max_length=12, choices=[("quiz", "Тест"), ("manual", "Вручную")])
    source_id = models.UUIDField(null=True, blank=True)
    title = models.CharField(max_length=255)
    max_score = models.DecimalField(max_digits=8, decimal_places=2)
    weight = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    position = models.PositiveIntegerField(default=0)


class Grade(UUIDModel, TimeStampedModel):
    gradebook_item = models.ForeignKey(
        GradebookItem, on_delete=models.CASCADE, related_name="grades"
    )
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="grades")
    score = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(
        max_length=12,
        choices=[("draft", "Черновик"), ("published", "Опубликована")],
        default="draft",
    )
    graded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    feedback = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["gradebook_item", "enrollment"], name="unique_grade")
        ]
        indexes = [models.Index(fields=["gradebook_item", "enrollment"])]
