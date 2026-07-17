from django.urls import path

from . import views

urlpatterns = [path("<uuid:quiz_id>/", views.take_quiz, name="take-quiz")]
