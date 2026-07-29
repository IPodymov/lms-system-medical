from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.assessments.permissions import can_view_gradebook
from apps.courses.models import CourseRunStaff
from apps.test_helpers import CourseFixture


class GradebookAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.data = CourseFixture.create(email="gradebook-student@test.local")
        cls.teacher = User.objects.create_user("gradebook-teacher@test.local", "pass")
        CourseRunStaff.objects.create(course_run=cls.data["run"], user=cls.teacher, role="teacher")

    def test_only_run_staff_or_course_editor_can_view_gradebook(self):
        self.assertFalse(can_view_gradebook(self.data["user"], self.data["run"]))
        self.assertTrue(can_view_gradebook(self.teacher, self.data["run"]))
        self.client.force_login(self.data["user"])
        response = self.client.get(reverse("gradebook", args=[self.data["run"].pk]))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.teacher)
        self.assertEqual(
            self.client.get(reverse("gradebook", args=[self.data["run"].pk])).status_code, 200
        )
