import json
from datetime import timedelta
from uuid import uuid4

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import ApplicationCommunicator
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.courses.models import Course, CourseRun
from apps.learning.models import Enrollment
from apps.notifications.models import Notification
from apps.organizations.models import Organization

from .consumers import CourseChatConsumer, DirectChatConsumer
from .models import CourseMessage, DirectMessage


class MessagingTests(TransactionTestCase):
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

    def test_direct_thread_shows_recipient_summary_before_message_form(self):
        self.client.force_login(self.sender)

        response = self.client.get(reverse("direct-message-thread", args=[self.recipient.pk]))

        self.assertContains(response, "Краткая информация о собеседнике")
        self.assertContains(response, f"@{self.recipient.username}")
        self.assertContains(response, self.recipient.email)

    def test_repeated_direct_message_post_with_same_token_creates_one_message(self):
        self.client.force_login(self.sender)
        url = reverse("direct-message-thread", args=[self.recipient.pk])
        payload = {"body": "Одно сообщение", "client_token": str(uuid4())}

        self.client.post(url, payload)
        self.client.post(url, payload)

        self.assertEqual(DirectMessage.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(type="direct_message").count(), 1)

    def test_contacts_are_limited_to_favorites_and_existing_dialogues(self):
        outsider = User.objects.create_user("outsider@example.test", "password")
        self.client.force_login(self.sender)

        response = self.client.get(reverse("direct-messages"))
        self.assertNotContains(response, self.recipient.email)
        self.assertNotContains(response, outsider.email)

        self.client.post(reverse("toggle-favorite-contact", args=[outsider.pk]))
        response = self.client.get(reverse("direct-messages"))
        self.assertContains(response, outsider.email)
        self.assertNotContains(response, self.recipient.email)

        self.client.post(
            reverse("direct-message-thread", args=[self.recipient.pk]), {"body": "Здравствуйте"}
        )
        response = self.client.get(reverse("direct-messages"))
        self.assertContains(response, self.recipient.email)

    def test_contact_search_finds_all_active_users_by_full_name(self):
        searched_user = User.objects.create_user(
            "ivanov@example.test",
            "password",
            first_name="Иван",
            last_name="Иванов",
            middle_name="Иванович",
        )
        self.client.force_login(self.sender)

        response = self.client.get(reverse("direct-messages"), {"q": "Иванов Иван"})

        self.assertContains(response, searched_user.get_full_name())
        self.assertNotContains(response, self.recipient.email)

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

    def test_direct_chat_websocket_persists_and_returns_a_message(self):
        async def communicate():
            communicator = ApplicationCommunicator(
                DirectChatConsumer.as_asgi(),
                {
                    "type": "websocket",
                    "path": f"/ws/messages/direct/{self.recipient.pk}/",
                    "headers": [],
                    "query_string": b"",
                    "user": self.sender,
                    "url_route": {"kwargs": {"user_id": str(self.recipient.pk)}},
                },
            )
            await communicator.send_input({"type": "websocket.connect"})
            self.assertEqual((await communicator.receive_output())["type"], "websocket.accept")
            await communicator.send_input(
                {
                    "type": "websocket.receive",
                    "text": json.dumps({"body": "Realtime", "client_token": str(uuid4())}),
                }
            )
            return await communicator.receive_output()

        response = async_to_sync(communicate)()

        self.assertEqual(response["type"], "websocket.send")
        self.assertEqual(json.loads(response["text"])["message"]["body"], "Realtime")
        self.assertTrue(DirectMessage.objects.filter(body="Realtime").exists())

    def test_course_chat_websocket_closes_when_access_is_revoked(self):
        async def communicate():
            communicator = ApplicationCommunicator(
                CourseChatConsumer.as_asgi(),
                {
                    "type": "websocket",
                    "path": f"/ws/messages/course/{self.course_run.pk}/",
                    "headers": [],
                    "query_string": b"",
                    "user": self.sender,
                    "url_route": {"kwargs": {"run_id": str(self.course_run.pk)}},
                },
            )
            await communicator.send_input({"type": "websocket.connect"})
            self.assertEqual((await communicator.receive_output())["type"], "websocket.accept")
            await database_sync_to_async(
                Enrollment.objects.filter(course_run=self.course_run, user=self.sender).delete
            )()
            await communicator.send_input(
                {
                    "type": "websocket.receive",
                    "text": json.dumps({"body": "Нет доступа", "client_token": str(uuid4())}),
                }
            )
            return await communicator.receive_output()

        response = async_to_sync(communicate)()

        self.assertEqual(response, {"type": "websocket.close", "code": 4403})
        self.assertFalse(CourseMessage.objects.filter(body="Нет доступа").exists())
