from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.courses.models import Course, CourseRun
from apps.learning.models import Enrollment
from apps.learning.services import EnrollmentError, enroll
from apps.organizations.models import Organization


class EnrollmentServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("student@test.local", "pass")
        org = Organization.objects.create(name="Test", short_name="T", slug="test")
        course = Course.objects.create(
            organization=org, title="Курс", slug="course", status="published", created_by=self.user
        )
        now = timezone.now()
        self.run = CourseRun.objects.create(
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
        enroll(course_run=self.run, user=self.user)
        enroll(course_run=self.run, user=self.user)
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_closed_enrollment_is_rejected(self):
        self.run.enrollment_end_at = timezone.now() - timedelta(seconds=1)
        self.run.save()
        with self.assertRaises(EnrollmentError):
            enroll(course_run=self.run, user=self.user)
