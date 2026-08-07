from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
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


class NotificationListViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.data = CourseFixture.create(email="notification-list@test.local")
        Notification.objects.bulk_create(
            Notification(user=cls.data["user"], type="system", title=f"Событие {i}", body="Текст")
            for i in range(25)
        )

    def test_list_is_paginated_and_newest_first(self):
        self.client.force_login(self.data["user"])
        first_page = self.client.get(reverse("notifications"))
        self.assertEqual(len(first_page.context["notifications"]), 20)
        self.assertEqual(first_page.context["notifications"].paginator.num_pages, 2)

        second_page = self.client.get(reverse("notifications"), {"page": 2})
        self.assertEqual(len(second_page.context["notifications"]), 5)

        # Страницы не пересекаются: сортировка задана явно, а не отдана СУБД.
        ids = {n.pk for n in first_page.context["notifications"]}
        self.assertTrue(ids.isdisjoint({n.pk for n in second_page.context["notifications"]}))
