from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import QuestionAnswer, Quiz, QuizAttempt


class QuizError(ValueError):
    pass


@transaction.atomic
def start_attempt(*, quiz: Quiz, enrollment) -> QuizAttempt:
    if enrollment.course_run.course_id != quiz.content_block.lesson.section.course_id:
        raise QuizError("Тест не относится к этому курсу.")
    last = (
        QuizAttempt.objects.select_for_update()
        .filter(quiz=quiz, enrollment=enrollment)
        .order_by("-attempt_number")
        .first()
    )
    number = (last.attempt_number if last else 0) + 1
    if number > quiz.attempt_limit:
        raise QuizError("Лимит попыток исчерпан.")
    return QuizAttempt.objects.create(quiz=quiz, enrollment=enrollment, attempt_number=number)


@transaction.atomic
def save_answer(*, attempt: QuizAttempt, question_id, answer_data: dict) -> QuestionAnswer:
    attempt = QuizAttempt.objects.select_for_update().get(pk=attempt.pk)
    if attempt.status != "started":
        raise QuizError("Попытка уже отправлена.")
    question = (
        attempt.quiz.quiz_questions.select_related("question").get(question_id=question_id).question
    )
    return QuestionAnswer.objects.update_or_create(
        attempt=attempt, question=question, defaults={"answer_data": answer_data}
    )[0]


@transaction.atomic
def submit_attempt(*, attempt: QuizAttempt) -> QuizAttempt:
    attempt = QuizAttempt.objects.select_for_update().select_related("quiz").get(pk=attempt.pk)
    if attempt.status in ("submitted", "checked"):
        return attempt
    total = Decimal("0")
    maximum = Decimal("0")
    for item in attempt.quiz.quiz_questions.select_related("question").prefetch_related(
        "question__options"
    ):
        maximum += item.points
        answer = attempt.answers.filter(question=item.question).first()
        correct = False
        data = answer.answer_data if answer else {}
        question = item.question
        if question.type in ("single_choice", "multiple_choice", "true_false"):
            selected = set(map(str, data.get("option_ids", [])))
            expected = {
                str(v)
                for v in question.options.filter(is_correct=True).values_list("id", flat=True)
            }
            correct = selected == expected
        elif question.type == "short_text":
            correct = str(data.get("text", "")).strip().casefold() in {
                str(x).strip().casefold() for x in question.settings.get("accepted_answers", [])
            }
        if answer:
            answer.is_correct = correct
            answer.score = item.points if correct else Decimal("0")
            answer.feedback = question.explanation if correct else ""
            answer.save()
        if correct:
            total += item.points
    attempt.score = total
    attempt.max_score = maximum
    attempt.passed = (total / maximum * 100 >= attempt.quiz.passing_score) if maximum else False
    attempt.status = "checked"
    attempt.submitted_at = timezone.now()
    attempt.save()
    return attempt
