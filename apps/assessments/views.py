from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.learning.models import Enrollment
from apps.learning.services import is_block_available, update_progress

from .models import Quiz
from .services import QuizError, save_answer, start_attempt, submit_attempt


@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(
        Quiz.objects.prefetch_related("quiz_questions__question__options"), pk=quiz_id
    )
    enrollment = get_object_or_404(
        Enrollment,
        user=request.user,
        course_run__course=quiz.content_block.lesson.section.course,
    )
    if not is_block_available(enrollment=enrollment, block=quiz.content_block):
        messages.error(request, "Сначала завершите материалы, которые идут перед этим тестом.")
        return redirect("course-learning", enrollment.pk)
    attempt = (
        quiz.attempts.filter(enrollment=enrollment, status="started")
        .order_by("-attempt_number")
        .first()
    )
    if not attempt:
        try:
            attempt = start_attempt(quiz=quiz, enrollment=enrollment)
        except QuizError as error:
            messages.error(request, str(error))
            return redirect("course-learning", enrollment.pk)
    questions = (
        quiz.quiz_questions.select_related("question")
        .prefetch_related("question__options")
        .order_by("position")
    )
    if request.method == "POST":
        try:
            for item in questions:
                value = request.POST.get(f"question_{item.question_id}")
                if value:
                    save_answer(
                        attempt=attempt,
                        question_id=item.question_id,
                        answer_data={"option_ids": [value]},
                    )
            attempt = submit_attempt(attempt=attempt)
            if attempt.passed:
                update_progress(enrollment=enrollment, block=quiz.content_block)
            return render(
                request,
                "assessments/result.html",
                {"attempt": attempt, "enrollment": enrollment},
            )
        except QuizError as error:
            messages.error(request, str(error))
    return render(
        request,
        "assessments/take_quiz.html",
        {
            "quiz": quiz,
            "attempt": attempt,
            "questions": questions,
            "enrollment": enrollment,
        },
    )
