from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.assessments.models import Question, QuestionOption, Quiz, QuizQuestion
from apps.courses.models import ContentBlock
from apps.learning.models import Enrollment
from apps.test_helpers import CourseFixture


class QuizMarkerRenderingTests(TestCase):
    """Координаты отметок на изображении обязаны попадать в CSS без локали.

    LANGUAGE_CODE = "ru", поэтому Django печатает Decimal с запятой: «25,0».
    CSS отбрасывает такое значение целиком, и все отметки схлопываются в
    левый верхний угол изображения — то есть вопрос становится непроходимым.
    """

    def setUp(self):
        fixture = CourseFixture.create()
        self.user = fixture["user"]
        self.enrollment: Enrollment = fixture["enrollment"]
        lesson = fixture["lesson"]

        block = ContentBlock.objects.create(
            lesson=lesson, title="Проверка", position=1, type="quiz"
        )
        self.quiz = Quiz.objects.create(content_block=block, title="Тест с изображением")
        question = Question.objects.create(
            organization=fixture["organization"],
            author=self.user,
            type="multiple_choice",
            text="Отметьте области",
            image="question_images/example.png",
        )
        QuestionOption.objects.create(
            question=question,
            text="Область 1",
            position=1,
            marker_x=Decimal("25.5"),
            marker_y=Decimal("30.0"),
            is_correct=True,
        )
        QuizQuestion.objects.create(quiz=self.quiz, question=question, position=1)
        self.client.force_login(self.user)

    def test_marker_coordinates_use_a_dot_not_a_comma(self):
        response = self.client.get(reverse("take-quiz", args=[self.quiz.id]))

        body = response.content.decode()
        self.assertIn("--marker-x: 25.5%", body)
        self.assertIn("--marker-y: 30.0%", body)
        # Ровно то, что ломало вёрстку до этого этапа.
        self.assertNotIn("25,5%", body)
        self.assertNotIn("30,0%", body)

    def test_marker_has_a_text_label_for_screen_readers(self):
        response = self.client.get(reverse("take-quiz", args=[self.quiz.id]))

        body = response.content.decode()
        # Внутри отметки только цифра, поэтому пояснение обязательно.
        self.assertIn("ui-visually-hidden", body)
        self.assertIn("Область 1", body)
