from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import User
from apps.courses.models import Course, CourseRun, CourseSection, Lesson
from apps.learning.models import Enrollment
from apps.organizations.models import Organization


class CourseFixture:
    """Small factory for fast, consistent course-domain tests."""

    @classmethod
    def create(cls, email="student@test.local", *, published=True):
        user = User.objects.create_user(email, "pass")
        organization = Organization.objects.create(
            name="Тестовая организация", short_name="ТО", slug=f"org-{user.pk.hex[:8]}"
        )
        course = Course.objects.create(
            organization=organization,
            title="Тестовый курс",
            slug=f"course-{user.pk.hex[:8]}",
            status=Course.Status.PUBLISHED if published else Course.Status.DRAFT,
            created_by=user,
        )
        now = timezone.now()
        run = CourseRun.objects.create(
            course=course,
            title="Основной поток",
            semester="1",
            academic_year="2026",
            start_at=now - timedelta(days=1),
            end_at=now + timedelta(days=30),
            enrollment_start_at=now - timedelta(days=1),
            enrollment_end_at=now + timedelta(days=1),
            status=CourseRun.Status.ACTIVE,
        )
        section = CourseSection.objects.create(
            course=course, title="Раздел 1", position=1, is_published=True
        )
        lesson = Lesson.objects.create(
            section=section, title="Тема 1", position=1, is_published=True
        )
        enrollment = Enrollment.objects.create(course_run=run, user=user)
        return {
            "user": user,
            "organization": organization,
            "course": course,
            "run": run,
            "section": section,
            "lesson": lesson,
            "enrollment": enrollment,
        }
