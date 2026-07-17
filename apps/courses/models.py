from django.conf import settings
from django.db import models

from apps.accounts.models import TimeStampedModel, UUIDModel
from apps.organizations.models import Organization


class Course(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликован"
        ARCHIVED = "archived", "Архив"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    slug = models.SlugField()
    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    cover = models.ImageField(upload_to="courses/", blank=True)
    status = models.CharField(max_length=12, choices=Status, default=Status.DRAFT)
    visibility = models.CharField(
        max_length=16,
        choices=[("private", "Приватный"), ("organization", "Организация")],
        default="organization",
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "slug"], name="unique_course_slug")
        ]

    def __str__(self):
        return self.title


class CourseAuthor(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="authors")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=12, choices=[("owner", "Владелец"), ("author", "Автор"), ("editor", "Редактор")]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course", "user"], name="unique_course_author")
        ]


class CourseRun(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        PLANNED = "planned", "Запланирован"
        ACTIVE = "active", "Активен"
        COMPLETED = "completed", "Завершён"
        ARCHIVED = "archived", "Архив"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="runs")
    title = models.CharField(max_length=255)
    semester = models.CharField(max_length=32)
    academic_year = models.CharField(max_length=16)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    enrollment_start_at = models.DateTimeField()
    enrollment_end_at = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status, default=Status.PLANNED)
    max_students = models.PositiveIntegerField(null=True, blank=True)
    settings = models.JSONField(default=dict, blank=True)


class CourseRunStaff(models.Model):
    course_run = models.ForeignKey(CourseRun, on_delete=models.CASCADE, related_name="staff")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=12, choices=[("teacher", "Преподаватель"), ("assistant", "Ассистент")]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course_run", "user"], name="unique_run_staff")
        ]


class CourseSection(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField()
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["course", "position"], name="unique_section_position")
        ]


class Lesson(TimeStampedModel):
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField()
    is_published = models.BooleanField(default=False)
    estimated_duration_minutes = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["section", "position"], name="unique_lesson_position")
        ]


class ContentBlock(TimeStampedModel):
    class Type(models.TextChoices):
        TEXT = "text", "Текст"
        VIDEO = "video", "Видео"
        FILE = "file", "Файл"
        QUIZ = "quiz", "Тест"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="blocks")
    type = models.CharField(max_length=12, choices=Type)
    title = models.CharField(max_length=255)
    position = models.PositiveIntegerField()
    is_required = models.BooleanField(default=True)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["lesson", "position"], name="unique_block_position")
        ]


class TextContent(models.Model):
    content_block = models.OneToOneField(
        ContentBlock, on_delete=models.CASCADE, related_name="text_content"
    )
    body = models.TextField()


class VideoContent(models.Model):
    content_block = models.OneToOneField(
        ContentBlock, on_delete=models.CASCADE, related_name="video_content"
    )
    file = models.FileField(upload_to="videos/", blank=True)
    external_url = models.URLField(blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)


class FileContent(models.Model):
    """Загруженный автором учебный материал."""

    content_block = models.OneToOneField(
        ContentBlock, on_delete=models.CASCADE, related_name="file_content"
    )
    file = models.FileField(upload_to="course_materials/")
    description = models.TextField(blank=True)
