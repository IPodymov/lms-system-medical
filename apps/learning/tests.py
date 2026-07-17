from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.assessments.models import Quiz
from apps.courses.models import ContentBlock, Course, CourseRun, CourseSection, Lesson, TextContent
from apps.learning.models import Enrollment
from apps.learning.services import EnrollmentError, enroll, is_block_available, update_progress
from apps.organizations.models import Organization


class EnrollmentServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("student@test.local", "pass")
        org = Organization.objects.create(name="Test", short_name="T", slug="test")
        course = Course.objects.create(
            organization=org, title="Курс", slug="course", status="published", created_by=self.user
        )
        now = timezone.now()
        self.course_run = CourseRun.objects.create(
            course=course,
            title="Поток",
            semester="1",
            academic_year="2026",
            start_at=now,
            end_at=now + timedelta(days=30),
            enrollment_start_at=now - timedelta(days=1),
            enrollment_end_at=now + timedelta(days=1),
            status="active",
            max_students=2,
        )

    def test_enrollment_is_idempotent(self):
        enroll(course_run=self.course_run, user=self.user)
        enroll(course_run=self.course_run, user=self.user)
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_closed_enrollment_is_rejected(self):
        self.course_run.enrollment_end_at = timezone.now() - timedelta(seconds=1)
        self.course_run.save()
        with self.assertRaises(EnrollmentError):
            enroll(course_run=self.course_run, user=self.user)


class CourseLearningNavigationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("student@test.local", "pass")
        organization = Organization.objects.create(name="Test", short_name="T", slug="test")
        course = Course.objects.create(
            organization=organization,
            title="Курс",
            slug="course",
            status="published",
            created_by=self.user,
        )
        now = timezone.now()
        run = CourseRun.objects.create(
            course=course,
            title="Поток",
            semester="1",
            academic_year="2026",
            start_at=now,
            end_at=now + timedelta(days=30),
            enrollment_start_at=now - timedelta(days=1),
            enrollment_end_at=now + timedelta(days=1),
            status="active",
        )
        self.enrollment = Enrollment.objects.create(course_run=run, user=self.user)
        section = CourseSection.objects.create(
            course=course, title="Раздел", position=1, is_published=True
        )
        lesson = Lesson.objects.create(section=section, title="Тема", position=1, is_published=True)
        self.lecture = ContentBlock.objects.create(
            lesson=lesson, type="text", title="Лекция", position=1
        )
        TextContent.objects.create(content_block=self.lecture, body="Содержание лекции")
        quiz_block = ContentBlock.objects.create(
            lesson=lesson, type="quiz", title="Проверка", position=2
        )
        self.quiz = Quiz.objects.create(content_block=quiz_block, title="Проверка")
        self.client.force_login(self.user)

    def test_quiz_opens_only_after_previous_material_is_completed(self):
        course_url = reverse("course-learning", args=[self.enrollment.pk])

        response = self.client.get(f"{course_url}?block={self.quiz.content_block_id}")
        self.assertEqual(response.context["current_block"].pk, self.lecture.pk)

        locked_response = self.client.get(reverse("take-quiz", args=[self.quiz.pk]))
        self.assertRedirects(locked_response, course_url)

        update_progress(enrollment=self.enrollment, block=self.lecture)
        response = self.client.get(f"{course_url}?block={self.quiz.content_block_id}")
        self.assertEqual(response.context["current_block"].pk, self.quiz.content_block_id)

    def test_unpublished_quiz_is_not_available(self):
        lesson = self.quiz.content_block.lesson
        lesson.is_published = False
        lesson.save(update_fields=["is_published"])

        self.assertFalse(
            is_block_available(enrollment=self.enrollment, block=self.quiz.content_block)
        )
