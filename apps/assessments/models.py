from django.conf import settings
from django.db import models

from apps.accounts.models import TimeStampedModel, UUIDModel
from apps.courses.models import ContentBlock
from apps.learning.models import Enrollment
from apps.organizations.models import Organization


class Quiz(UUIDModel, TimeStampedModel):
    content_block = models.OneToOneField(
        ContentBlock, on_delete=models.CASCADE, related_name="quiz"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    attempt_limit = models.PositiveIntegerField(default=1)
    time_limit_seconds = models.PositiveIntegerField(null=True, blank=True)
    passing_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    shuffle_questions = models.BooleanField(default=False)
    show_answers_after_submission = models.BooleanField(default=False)


class Question(UUIDModel, TimeStampedModel):
    class Type(models.TextChoices):
        SINGLE = "single_choice", "Один вариант"
        MULTIPLE = "multiple_choice", "Несколько вариантов"
        TRUE_FALSE = "true_false", "Верно/неверно"
        SHORT = "short_text", "Короткий ответ"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    type = models.CharField(max_length=20, choices=Type)
    text = models.TextField()
    explanation = models.TextField(blank=True)
    difficulty = models.PositiveSmallIntegerField(default=1)
    settings = models.JSONField(default=dict, blank=True)


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=1000)
    position = models.PositiveIntegerField()
    is_correct = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="quiz_questions")
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    position = models.PositiveIntegerField()
    points = models.DecimalField(max_digits=7, decimal_places=2, default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["quiz", "question"], name="unique_quiz_question")
        ]


class QuizAttempt(UUIDModel, TimeStampedModel):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="attempts")
    attempt_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=12,
        choices=[
            ("started", "Начата"),
            ("submitted", "Отправлена"),
            ("checked", "Проверена"),
            ("expired", "Истекла"),
        ],
        default="started",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    passed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["quiz", "enrollment", "attempt_number"],
                name="unique_attempt_number",
            )
        ]
        indexes = [models.Index(fields=["enrollment", "quiz", "status"])]


class QuestionAnswer(TimeStampedModel):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    answer_data = models.JSONField(default=dict)
    score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_correct = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="unique_question_answer")
        ]
