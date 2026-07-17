from datetime import timedelta
from uuid import uuid4

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.courses.models import Course, CourseRun
from apps.learning.models import Enrollment
from apps.notifications.models import Notification
from apps.organizations.models import Organization

from .models import CourseMessage, DirectMessage


class MessagingTests(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user("sender@example.test", "password")
        self.recipient = User.objects.create_user("recipient@example.test", "password")
        organization = Organization.objects.create(name="Тест", short_name="Тест", slug="test-org")
        course = Course.objects.create(
            organization=organization,
            title="Курс",
            slug="course",
            status="published",
            created_by=self.sender,
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
        )
        Enrollment.objects.create(course_run=self.course_run, user=self.sender)
        Enrollment.objects.create(course_run=self.course_run, user=self.recipient)

    def test_direct_message_creates_recipient_notification(self):
        self.client.force_login(self.sender)
        response = self.client.post(
            reverse("direct-message-thread", args=[self.recipient.pk]), {"body": "Здравствуйте"}
        )
        self.assertRedirects(response, reverse("direct-message-thread", args=[self.recipient.pk]))
        self.assertEqual(DirectMessage.objects.count(), 1)
        self.assertTrue(
            Notification.objects.filter(user=self.recipient, type="direct_message").exists()
        )

    def test_repeated_direct_message_post_with_same_token_creates_one_message(self):
        self.client.force_login(self.sender)
        url = reverse("direct-message-thread", args=[self.recipient.pk])
        payload = {"body": "Одно сообщение", "client_token": str(uuid4())}

        self.client.post(url, payload)
        self.client.post(url, payload)

        self.assertEqual(DirectMessage.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(type="direct_message").count(), 1)

    def test_course_chat_is_available_only_to_course_participants(self):
        self.client.force_login(self.sender)
        response = self.client.post(
            reverse("course-chat", args=[self.course_run.pk]), {"body": "Вопрос"}
        )
        self.assertRedirects(response, reverse("course-chat", args=[self.course_run.pk]))
        self.assertEqual(CourseMessage.objects.count(), 1)
        self.assertTrue(
            Notification.objects.filter(user=self.recipient, type="course_chat").exists()
        )

        outsider = User.objects.create_user("outsider@example.test", "password")
        self.client.force_login(outsider)
        response = self.client.get(reverse("course-chat", args=[self.course_run.pk]))
        self.assertEqual(response.status_code, 403)
