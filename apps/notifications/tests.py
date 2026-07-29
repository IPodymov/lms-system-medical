from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.tasks import create_notification, remind_inactive_learners
from apps.test_helpers import CourseFixture


class NotificationTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.data = CourseFixture.create(email="notification@test.local")

    def test_create_notification_task_persists_notification(self):
        create_notification.run(str(self.data["user"].pk), "system", "Заголовок", "Сообщение")
        item = Notification.objects.get(user=self.data["user"])
        self.assertEqual(item.type, "system")
        self.assertEqual(item.body, "Сообщение")

    def test_inactive_reminder_is_created_once_per_day(self):
        enrollment = self.data["enrollment"]
        type(enrollment).objects.filter(pk=enrollment.pk).update(
            updated_at=timezone.now() - timedelta(days=8)
        )
        self.assertEqual(remind_inactive_learners(days=7), 1)
        self.assertEqual(remind_inactive_learners(days=7), 0)
        self.assertEqual(Notification.objects.filter(type="course_reminder").count(), 1)

    def test_recent_or_completed_enrollment_is_not_reminded(self):
        self.assertEqual(remind_inactive_learners(days=7), 0)
        self.data["enrollment"].progress_percent = 100
        self.data["enrollment"].save(update_fields=["progress_percent"])
        type(self.data["enrollment"]).objects.filter(pk=self.data["enrollment"].pk).update(
            updated_at=timezone.now() - timedelta(days=8)
        )
        self.assertEqual(remind_inactive_learners(days=7), 0)
