from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from apps.messaging.models import DirectMessage
from apps.messaging.realtime import course_room_name, direct_room_name
from apps.messaging.services import (
    create_course_message,
    create_direct_message,
    serialize_direct_message,
)
from apps.notifications.models import Notification
from apps.test_helpers import CourseFixture


class MessagingServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.data = CourseFixture.create(email="sender@test.local")
        cls.recipient_data = CourseFixture.create(email="recipient@test.local")

    def test_direct_message_is_idempotent_and_notifies_recipient(self):
        token = uuid4()
        message, created = create_direct_message(
            sender=self.data["user"],
            recipient=self.recipient_data["user"],
            body="Привет",
            client_token=token,
        )
        duplicate, duplicate_created = create_direct_message(
            sender=self.data["user"],
            recipient=self.recipient_data["user"],
            body="Другое тело",
            client_token=token,
        )
        self.assertTrue(created)
        self.assertFalse(duplicate_created)
        self.assertEqual(message.pk, duplicate.pk)
        self.assertEqual(DirectMessage.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.recipient_data["user"]).count(), 1)

    def test_course_message_notifies_active_participants_except_author(self):
        token = uuid4()
        message, created = create_course_message(
            course_run=self.data["run"],
            author=self.recipient_data["user"],
            body="Важное сообщение",
            client_token=token,
        )
        self.assertTrue(created)
        self.assertEqual(message.body, "Важное сообщение")
        self.assertEqual(
            Notification.objects.filter(user=self.data["user"], type="course_chat").count(), 1
        )
        self.assertEqual(
            Notification.objects.filter(
                user=self.recipient_data["user"], type="course_chat"
            ).count(),
            0,
        )

    def test_room_names_are_stable_for_direct_messages(self):
        first = self.data["user"].pk
        second = self.recipient_data["user"].pk
        self.assertEqual(direct_room_name(first, second), direct_room_name(second, first))
        self.assertEqual(course_room_name(self.data["run"].pk), f"course.{self.data['run'].pk.hex}")


class MessageSerializationTests(TestCase):
    """Время у сообщения, пришедшего сокетом, и у него же после перезагрузки.

    Оба пути показывают одно сообщение, но разными средствами: шаблон
    печатает `created_at` в TIME_ZONE, сериализатор — строкой. Пока строка
    строилась без localtime, время расходилось ровно на смещение часового
    пояса, и переписка выглядела так, будто ответ пришёл раньше вопроса.
    """

    @classmethod
    def setUpTestData(cls):
        cls.data = CourseFixture.create(email="serialize@test.local")

    def test_created_at_is_serialized_in_the_projects_timezone(self):
        message = DirectMessage.objects.create(
            sender=self.data["user"],
            recipient=self.data["user"],
            body="Время",
        )

        payload = serialize_direct_message(message)

        expected = timezone.localtime(message.created_at).strftime("%d.%m %H:%M")
        self.assertEqual(payload["created_at"], expected)
        self.assertNotEqual(timezone.get_current_timezone_name(), "UTC")
