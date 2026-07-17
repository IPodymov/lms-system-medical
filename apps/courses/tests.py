from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.assessments.models import Quiz
from apps.organizations.models import Organization, OrganizationMembership

from .models import ContentBlock, Course, CourseMaterialLink, FileContent, TextContent


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
        edit_response = self.client.get(reverse("course-edit", args=[course.pk]))
        self.assertEqual(edit_response.status_code, 200)
        self.assertContains(
            edit_response,
            reverse("course-detail", args=[course.pk]),
        )
        self.assertContains(edit_response, "Открыть черновик курса")
        self.assertEqual(course.short_description, "Введение")
        self.assertEqual(course.description, "Описание курса")
        self.assertTrue(course.authors.filter(user=self.user, role="owner").exists())

    def test_author_can_create_course_with_long_title(self):
        title = "a" * 255

        response = self.client.post(reverse("course-create"), {"title": title})

        course = Course.objects.get(title=title)
        self.assertRedirects(response, reverse("course-edit", args=[course.pk]))
        self.assertEqual(course.slug, "a" * 50)

    def test_long_course_slugs_remain_unique(self):
        title = "a" * 255
        Course.objects.create(
            organization=self.organization,
            title="Первый курс",
            slug="a" * 50,
            created_by=self.user,
        )

        self.client.post(reverse("course-create"), {"title": title})

        course = Course.objects.get(title=title)
        self.assertEqual(course.slug, f"{'a' * 48}-2")

    def test_author_can_add_first_lesson_and_material_when_creating_course(self):
        response = self.client.post(
            reverse("course-create"),
            {
                "title": "Анатомия",
                "lesson_title": "Строение сердца",
                "lesson_content": "Текст лекции",
                "material_title": "Атлас",
                "material_file": SimpleUploadedFile("atlas.pdf", b"pdf"),
            },
        )

        course = Course.objects.get(title="Анатомия")
        self.assertRedirects(response, reverse("course-edit", args=[course.pk]))
        self.assertTrue(course.sections.filter(lessons__title="Строение сердца").exists())
        self.assertTrue(TextContent.objects.filter(body="Текст лекции").exists())
        self.assertTrue(FileContent.objects.filter(content_block__title="Атлас").exists())

    def test_editor_can_add_text_block_to_a_topic(self):
        course = Course.objects.create(
            organization=self.organization,
            title="Курс",
            slug="course",
            created_by=self.user,
        )
        course.authors.create(user=self.user, role="owner")
        self.client.post(
            reverse("course-edit", args=[course.pk]),
            {"action": "add_lesson", "section_title": "Раздел", "lesson_title": "Тема"},
        )
        lesson = course.sections.get(title="Раздел").lessons.get(title="Тема")

        response = self.client.post(
            reverse("course-edit", args=[course.pk]),
            {
                "action": "add_text",
                "lesson_id": lesson.pk,
                "text_title": "Основные понятия",
                "text_body": "Текст лекции",
            },
        )

        self.assertRedirects(response, reverse("course-edit", args=[course.pk]))
        self.assertTrue(
            TextContent.objects.filter(
                content_block__lesson=lesson,
                content_block__title="Основные понятия",
                body="Текст лекции",
            ).exists()
        )

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

    def test_editor_can_add_external_material_link(self):
        course = Course.objects.create(
            organization=self.organization, title="Курс", slug="course", created_by=self.user
        )
        course.authors.create(user=self.user, role="owner")

        response = self.client.post(
            reverse("course-edit", args=[course.pk]),
            {
                "action": "add_material_link",
                "link_title": "Клинические рекомендации",
                "link_url": "https://example.test/guidelines",
                "link_description": "Актуальная редакция",
            },
        )

        self.assertRedirects(response, reverse("course-edit", args=[course.pk]))
        self.assertTrue(
            CourseMaterialLink.objects.filter(
                course=course, title="Клинические рекомендации"
            ).exists()
        )

    def test_author_can_create_quiz_on_separate_page(self):
        course = Course.objects.create(
            organization=self.organization, title="Курс", slug="course", created_by=self.user
        )
        course.authors.create(user=self.user, role="owner")
        response = self.client.post(
            reverse("quiz-create", args=[course.pk]),
            {
                "quiz_title": "Тест по теме",
                "question_text": "Какой ответ верный?",
                "option": ["Первый", "Второй"],
                "correct_option": "1",
            },
        )

        self.assertRedirects(response, reverse("course-edit", args=[course.pk]))
        self.assertTrue(Quiz.objects.filter(title="Тест по теме").exists())
