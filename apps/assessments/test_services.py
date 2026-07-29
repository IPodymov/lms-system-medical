from decimal import Decimal

from django.test import TestCase

from apps.courses.models import ContentBlock
from apps.test_helpers import CourseFixture

from .models import (
    Question,
    QuestionAnswer,
    QuestionOption,
    Quiz,
    QuizQuestion,
)
from .services import QuizError, save_answer, start_attempt, submit_attempt


class QuizServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.data = CourseFixture.create()
        cls.block = ContentBlock.objects.create(
            lesson=cls.data["lesson"], type=ContentBlock.Type.QUIZ, title="Тест", position=1
        )
        cls.quiz = Quiz.objects.create(
            content_block=cls.block, title="Тест", attempt_limit=1, passing_score=50
        )
        cls.question = Question.objects.create(
            organization=cls.data["organization"],
            author=cls.data["user"],
            type=Question.Type.MULTIPLE,
            text="Выберите варианты",
            explanation="Верно",
        )
        cls.correct = QuestionOption.objects.create(
            question=cls.question, text="Да", position=1, is_correct=True
        )
        cls.other_correct = QuestionOption.objects.create(
            question=cls.question, text="Тоже да", position=2, is_correct=True
        )
        QuestionOption.objects.create(question=cls.question, text="Нет", position=3)
        QuizQuestion.objects.create(quiz=cls.quiz, question=cls.question, position=1)

    def test_attempt_limit_is_enforced(self):
        attempt = start_attempt(quiz=self.quiz, enrollment=self.data["enrollment"])
        self.assertEqual(attempt.attempt_number, 1)
        with self.assertRaisesMessage(QuizError, "Лимит попыток исчерпан"):
            start_attempt(quiz=self.quiz, enrollment=self.data["enrollment"])

    def test_save_answer_is_idempotent_and_submit_checks_multiple_choice(self):
        attempt = start_attempt(quiz=self.quiz, enrollment=self.data["enrollment"])
        answer = save_answer(
            attempt=attempt,
            question_id=self.question.pk,
            answer_data={"option_ids": [str(self.correct.pk), str(self.other_correct.pk)]},
        )
        save_answer(
            attempt=attempt,
            question_id=self.question.pk,
            answer_data={"option_ids": [str(self.correct.pk), str(self.other_correct.pk)]},
        )
        self.assertEqual(QuestionAnswer.objects.filter(attempt=attempt).count(), 1)
        result = submit_attempt(attempt=attempt)
        answer.refresh_from_db()
        self.assertEqual(result.status, "checked")
        self.assertTrue(answer.is_correct)
        self.assertEqual(answer.score, Decimal("1"))
        self.assertTrue(result.passed)

    def test_submitted_attempt_cannot_be_changed_and_submit_is_idempotent(self):
        attempt = start_attempt(quiz=self.quiz, enrollment=self.data["enrollment"])
        submit_attempt(attempt=attempt)
        with self.assertRaisesMessage(QuizError, "Попытка уже отправлена"):
            save_answer(attempt=attempt, question_id=self.question.pk, answer_data={})
        self.assertEqual(submit_attempt(attempt=attempt).status, "checked")

    def test_attempt_rejects_quiz_from_another_course(self):
        other = CourseFixture.create(email="other@test.local")
        with self.assertRaisesMessage(QuizError, "не относится"):
            start_attempt(quiz=self.quiz, enrollment=other["enrollment"])
