from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.assessments.models import Question, Quiz
from apps.learning.models import Enrollment
from apps.organizations.models import Organization, OrganizationMembership

from .models import (
    ContentBlock,
    Course,
    CourseEnrollmentLink,
    CourseMaterialLink,
    CourseRun,
    FileContent,
    TextContent,
)


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
        self.assertContains(edit_response, "Открыть черновик")
        self.assertContains(edit_response, "Открыть курс для записи")
        self.assertEqual(course.short_description, "Введение")
        self.assertEqual(course.description, "Описание курса")
        self.assertTrue(course.authors.filter(user=self.user, role="owner").exists())

    def test_author_can_create_course_with_long_title(self):
        title = "a" * 255

        response = self.client.post(reverse("course-create"), {"title": title})

        course = Course.objects.get(title=title)
        self.assertRedirects(response, reverse("course-edit", args=[course.pk]))
        self.assertEqual(course.slug, "a" * 50)

    def test_author_can_set_schedule_when_creating_and_editing_course(self):
        response = self.client.post(
            reverse("course-create"),
            {
                "title": "Курс со сроками",
                "course_start": "2026-09-01",
                "course_end": "2026-12-25",
            },
        )

        course = Course.objects.get(title="Курс со сроками")
        self.assertRedirects(response, reverse("course-edit", args=[course.pk]))
        run = CourseRun.objects.get(course=course)
        self.assertEqual(run.status, CourseRun.Status.PLANNED)
        self.assertEqual(timezone.localtime(run.start_at).date().isoformat(), "2026-09-01")
        self.assertEqual(timezone.localtime(run.end_at).date().isoformat(), "2026-12-25")

        response = self.client.post(
            reverse("course-edit", args=[course.pk]),
            {
                "action": "save_schedule",
                "course_start": "2026-09-15",
                "course_end": "2027-01-15",
            },
        )

        self.assertRedirects(response, reverse("course-edit", args=[course.pk]))
        run.refresh_from_db()
        self.assertEqual(timezone.localtime(run.start_at).date().isoformat(), "2026-09-15")
        self.assertEqual(timezone.localtime(run.end_at).date().isoformat(), "2027-01-15")

    def test_author_sees_own_draft_in_catalog(self):
        course = Course.objects.create(
            organization=self.organization,
            title="Черновик фармакологии",
            slug="pharmacology-draft",
            created_by=self.user,
        )
        course.authors.create(user=self.user, role="owner")

        response = self.client.get(reverse("course-catalog"))

        self.assertContains(response, "Черновики курсов")
        self.assertContains(response, "Черновик фармакологии")
        self.assertContains(response, reverse("course-edit", args=[course.pk]))

    def test_publishing_course_creates_active_run_visible_to_student(self):
        course = Course.objects.create(
            organization=self.organization,
            title="Открытый курс",
            slug="open-course",
            created_by=self.user,
        )
        course.authors.create(user=self.user, role="owner")

        response = self.client.post(
            reverse("course-edit", args=[course.pk]),
            {
                "action": "save_course",
                "title": course.title,
                "status": Course.Status.PUBLISHED,
            },
        )

        self.assertRedirects(response, reverse("course-edit", args=[course.pk]))
        run = CourseRun.objects.get(course=course)
        self.assertEqual(run.status, CourseRun.Status.ACTIVE)
        self.assertTrue(run.staff.filter(user=self.user, role="teacher").exists())

        student = User.objects.create_user("student@example.test", "password")
        self.client.force_login(student)
        response = self.client.get(reverse("course-catalog"))

        self.assertContains(response, "Открытый курс")
        self.assertContains(response, reverse("enroll", args=[run.pk]))

    def test_authenticated_student_can_enroll_using_an_active_link(self):
        course = Course.objects.create(
            organization=self.organization,
            title="Курс по ссылке",
            slug="link-course",
            created_by=self.user,
            status=Course.Status.PUBLISHED,
        )
        now = timezone.now()
        course_run = CourseRun.objects.create(
            course=course,
            title="Основной поток",
            semester="1",
            academic_year="2026",
            start_at=now,
            end_at=now + timedelta(days=30),
            enrollment_start_at=now - timedelta(days=1),
            enrollment_end_at=now + timedelta(days=1),
            status=CourseRun.Status.ACTIVE,
        )
        enrollment_link = CourseEnrollmentLink.objects.create(
            course_run=course_run, created_by=self.user, label="Тестовая ссылка"
        )
        student = User.objects.create_user("student@example.test", "password")
        self.client.force_login(student)

        response = self.client.get(reverse("enroll-by-link", args=[enrollment_link.pk]))
        self.assertContains(response, "Курс по ссылке")
        response = self.client.post(reverse("enroll-by-link", args=[enrollment_link.pk]))

        self.assertRedirects(response, reverse("my-courses"))
        self.assertTrue(
            Enrollment.objects.filter(
                course_run=course_run, user=student, enrollment_source="link"
            ).exists()
        )

    def test_author_can_open_course_and_add_self_as_learner(self):
        course = Course.objects.create(
            organization=self.organization,
            title="Курс преподавателя",
            slug="teacher-course",
            created_by=self.user,
        )
        course.authors.create(user=self.user, role="owner")
        edit_url = reverse("course-edit", args=[course.pk])

        response = self.client.post(edit_url, {"action": "open_enrollment"})

        self.assertRedirects(response, edit_url)
        course.refresh_from_db()
        self.assertEqual(course.status, Course.Status.PUBLISHED)
        run = CourseRun.objects.get(course=course, status=CourseRun.Status.ACTIVE)

        response = self.client.post(edit_url, {"action": "enroll_editor"})

        self.assertRedirects(response, edit_url)
        self.assertTrue(Enrollment.objects.filter(course_run=run, user=self.user).exists())

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

    def test_editor_can_delete_block_and_remaining_blocks_are_repositioned(self):
        course = Course.objects.create(
            organization=self.organization, title="Курс", slug="course", created_by=self.user
        )
        course.authors.create(user=self.user, role="owner")
        self.client.post(
            reverse("course-edit", args=[course.pk]),
            {"action": "add_lesson", "section_title": "Раздел", "lesson_title": "Тема"},
        )
        lesson = course.sections.get().lessons.get()
        first_block = ContentBlock.objects.create(
            lesson=lesson, type=ContentBlock.Type.TEXT, title="Первый", position=1
        )
        remaining_block = ContentBlock.objects.create(
            lesson=lesson, type=ContentBlock.Type.TEXT, title="Второй", position=2
        )

        response = self.client.post(
            reverse("course-edit", args=[course.pk]),
            {"action": "delete_block", "delete_block_id": first_block.pk},
        )

        self.assertRedirects(response, reverse("course-edit", args=[course.pk]))
        self.assertFalse(ContentBlock.objects.filter(pk=first_block.pk).exists())
        remaining_block.refresh_from_db()
        self.assertEqual(remaining_block.position, 1)

    def test_editor_can_edit_and_reorder_lessons(self):
        course = Course.objects.create(
            organization=self.organization, title="Курс", slug="course", created_by=self.user
        )
        course.authors.create(user=self.user, role="owner")
        url = reverse("course-edit", args=[course.pk])
        self.client.post(
            url, {"action": "add_lesson", "section_title": "Раздел", "lesson_title": "Первая"}
        )
        self.client.post(
            url, {"action": "add_lesson", "section_title": "Раздел", "lesson_title": "Вторая"}
        )
        section = course.sections.get(title="Раздел")
        first_lesson, second_lesson = section.lessons.order_by("position")

        self.client.post(
            url,
            {
                "action": "edit_lesson",
                "lesson_id": first_lesson.pk,
                "lesson_title": "Обновлённая тема",
                "lesson_description": "Новое описание",
            },
        )
        response = self.client.post(
            url,
            {
                "action": "reorder_lessons",
                "section_id": section.pk,
                "lesson_id": [second_lesson.pk, first_lesson.pk],
            },
        )

        self.assertRedirects(response, url)
        first_lesson.refresh_from_db()
        second_lesson.refresh_from_db()
        self.assertEqual(first_lesson.title, "Обновлённая тема")
        self.assertEqual(first_lesson.description, "Новое описание")
        self.assertEqual(second_lesson.position, 1)
        self.assertEqual(first_lesson.position, 2)

    def test_editor_can_edit_and_reorder_text_blocks(self):
        course = Course.objects.create(
            organization=self.organization, title="Курс", slug="course", created_by=self.user
        )
        course.authors.create(user=self.user, role="owner")
        url = reverse("course-edit", args=[course.pk])
        self.client.post(
            url, {"action": "add_lesson", "section_title": "Раздел", "lesson_title": "Тема"}
        )
        lesson = course.sections.get().lessons.get()
        first_block = ContentBlock.objects.create(
            lesson=lesson, type=ContentBlock.Type.TEXT, title="Первый", position=1
        )
        second_block = ContentBlock.objects.create(
            lesson=lesson, type=ContentBlock.Type.TEXT, title="Второй", position=2
        )
        TextContent.objects.create(content_block=first_block, body="Старый текст")
        TextContent.objects.create(content_block=second_block, body="Второй текст")

        self.client.post(
            url,
            {
                "action": "edit_block",
                "block_id": first_block.pk,
                "block_title": "Обновлённый блок",
                "text_body": "Новый текст",
            },
        )
        response = self.client.post(
            url,
            {
                "action": "reorder_blocks",
                "lesson_id": lesson.pk,
                "block_id": [second_block.pk, first_block.pk],
            },
        )

        self.assertRedirects(response, url)
        first_block.refresh_from_db()
        second_block.refresh_from_db()
        self.assertEqual(first_block.title, "Обновлённый блок")
        self.assertEqual(first_block.text_content.body, "Новый текст")
        self.assertEqual(second_block.position, 1)
        self.assertEqual(first_block.position, 2)

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
        page_response = self.client.get(reverse("quiz-create", args=[course.pk]))

        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, "Создать тест")

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

    def test_author_can_create_image_question_with_multiple_answers(self):
        course = Course.objects.create(
            organization=self.organization, title="Курс", slug="course", created_by=self.user
        )
        course.authors.create(user=self.user, role="owner")

        response = self.client.post(
            reverse("quiz-create", args=[course.pk]),
            {
                "quiz_title": "Изображение",
                "question_text": "Отметьте структуры",
                "question_kind": "image",
                "answer_mode": "multiple",
                "marker_x": ["12.5", "75"],
                "marker_y": ["20", "80.5"],
                "correct_option": ["0", "1"],
                "question_image": SimpleUploadedFile("diagram.png", b"image", "image/png"),
            },
        )

        self.assertRedirects(response, reverse("course-edit", args=[course.pk]))
        question = Quiz.objects.get(title="Изображение").quiz_questions.get().question
        self.assertEqual(question.type, Question.Type.MULTIPLE)
        self.assertTrue(question.image)
        self.assertEqual(question.options.filter(is_correct=True).count(), 2)
        self.assertEqual(question.options.get(position=1).marker_x, 12.5)
