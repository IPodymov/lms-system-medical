from django.contrib import admin

from .models import (
    Question,
    QuestionAnswer,
    QuestionOption,
    Quiz,
    QuizAttempt,
    QuizQuestion,
)

admin.site.register([Quiz, Question, QuestionOption, QuizQuestion, QuizAttempt, QuestionAnswer])
