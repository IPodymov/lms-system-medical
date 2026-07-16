from django.contrib import admin
from .models import Quiz,Question,QuestionOption,QuizQuestion,QuizAttempt,QuestionAnswer
admin.site.register([Quiz,Question,QuestionOption,QuizQuestion,QuizAttempt,QuestionAnswer])
