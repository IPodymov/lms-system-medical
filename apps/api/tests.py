from django.test import TestCase
from rest_framework.test import APIClient

from apps.assessments.models import Question, QuestionOption, Quiz, QuizQuestion
from apps.courses.models import ContentBlock
from apps.notifications.models import Notification
from apps.test_helpers import CourseFixture


class ApiWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.data = CourseFixture.create(email="api-student@test.local")
        cls.client = APIClient()
        block = ContentBlock.objects.create(
            lesson=cls.data["lesson"], type=ContentBlock.Type.QUIZ, title="API тест", position=1
        )
        cls.quiz = Quiz.objects.create(content_block=block, title="API тест", passing_score=0)
        question = Question.objects.create(
            organization=cls.data["organization"],
            author=cls.data["user"],
            type=Question.Type.SINGLE,
            text="Вопрос",
        )
        QuestionOption.objects.create(question=question, text="Ответ", position=1, is_correct=True)
        QuizQuestion.objects.create(quiz=cls.quiz, question=question, position=1)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.data["user"])

    def test_me_catalog_and_user_scoped_notifications(self):
        Notification.objects.create(
            user=self.data["user"], type="system", title="Для меня", body="Текст"
        )
        response = self.client.get("/api/v1/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], self.data["user"].email)
        self.assertEqual(self.client.get("/api/v1/courses/").status_code, 200)
        notifications = self.client.get("/api/v1/notifications/")
        self.assertEqual(notifications.status_code, 200)
        self.assertEqual(len(notifications.data), 1)

    def test_enrollment_is_idempotent_and_attempt_workflow_is_scoped(self):
        response = self.client.post(
            "/api/v1/enrollments/", {"course_run": str(self.data["run"].pk)}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self.client.post(
                "/api/v1/enrollments/", {"course_run": str(self.data["run"].pk)}, format="json"
            ).status_code,
            201,
        )
        response = self.client.post(f"/api/v1/quizzes/{self.quiz.pk}/attempts/")
        self.assertEqual(response.status_code, 201)
        attempt_id = response.data["id"]
        answer = self.client.put(
            f"/api/v1/attempts/{attempt_id}/answers/",
            {"question_id": str(self.quiz.quiz_questions.first().question_id), "answer_data": {}},
            format="json",
        )
        self.assertEqual(answer.status_code, 204)
        submitted = self.client.post(f"/api/v1/attempts/{attempt_id}/submit/")
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.data["status"], "checked")

    def test_anonymous_api_requests_are_rejected(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/v1/me/").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/courses/").status_code, 403)
