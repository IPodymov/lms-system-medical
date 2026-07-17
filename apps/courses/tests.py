from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.assessments.models import Quiz
from apps.organizations.models import Organization, OrganizationMembership

from .models import ContentBlock, Course, FileContent


class CourseAuthoringViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("teacher@example.test", "password")
        self.organization = Organization.objects.create(
            name="Тестовый университет", short_name="ТУ", slug="test-university"
        )
        OrganizationMembership.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMembership.Role.TEACHER,
        )
        self.client.force_login(self.user)

    def test_author_can_create_course_with_description(self):
        response = self.client.post(
            reverse("course-create"),
            {
                "title": "Фармакология",
                "short_description": "Введение",
                "description": "Описание курса",
            },
        )

        course = Course.objects.get(title="Фармакология")
        self.assertRedirects(response, reverse("course-edit", args=[course.pk]))
        self.assertEqual(course.short_description, "Введение")
        self.assertEqual(course.description, "Описание курса")
        self.assertTrue(course.authors.filter(user=self.user, role="owner").exists())

    def test_editor_adds_material_and_quiz(self):
        course = Course.objects.create(
            organization=self.organization,
            title="Курс",
            slug="course",
            created_by=self.user,
        )
        course.authors.create(user=self.user, role="owner")
        url = reverse("course-edit", args=[course.pk])

        self.client.post(
            url,
            {
                "action": "add_material",
                "material_title": "Конспект",
                "file": SimpleUploadedFile("notes.txt", b"material"),
            },
        )
        self.client.post(
            url,
            {
                "action": "add_quiz",
                "quiz_title": "Проверка",
                "question_text": "Верный ответ?",
                "option": ["Да", "Нет", "", ""],
                "correct_option": "0",
            },
        )

        self.assertEqual(FileContent.objects.count(), 1)
        self.assertTrue(ContentBlock.objects.filter(type="file").exists())
        quiz = Quiz.objects.get(title="Проверка")
        self.assertTrue(quiz.quiz_questions.get().question.options.get(position=1).is_correct)
