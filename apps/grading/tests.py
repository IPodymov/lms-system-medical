from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.assessments.permissions import can_view_gradebook
from apps.courses.models import CourseRunStaff
from apps.learning.models import Enrollment
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


class GradebookRenderingTests(TestCase):
    """Журнал — первая страница проекта в плотном режиме.

    Плотность и ширина включаются атрибутами на <main>; значения приходят
    из tokens.css. Если атрибут потеряется, страница молча вернётся к
    обычным отступам — глазами это заметно не сразу, тестом заметно всегда.
    """

    @classmethod
    def setUpTestData(cls):
        cls.data = CourseFixture.create(email="gradebook-render@test.local")
        cls.teacher = User.objects.create_user("gradebook-render-teacher@test.local", "pass")
        CourseRunStaff.objects.create(course_run=cls.data["run"], user=cls.teacher, role="teacher")

    def test_page_is_dense_and_wide_and_lists_learners(self):
        self.client.force_login(self.teacher)

        response = self.client.get(reverse("gradebook", args=[self.data["run"].pk]))

        self.assertContains(response, 'data-density="compact"')
        self.assertContains(response, 'data-width="wide"')
        self.assertContains(response, self.data["user"].email)
        self.assertContains(response, "ui-table__num")

    def test_empty_run_shows_an_empty_state_instead_of_a_headerless_table(self):
        Enrollment.objects.filter(course_run=self.data["run"]).delete()
        self.client.force_login(self.teacher)

        response = self.client.get(reverse("gradebook", args=[self.data["run"].pk]))

        self.assertContains(response, "На поток пока никто не записан")
        self.assertNotContains(response, "ui-table-wrap")
