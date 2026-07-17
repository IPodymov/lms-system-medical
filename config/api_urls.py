from django.urls import path

from apps.api import views

urlpatterns = [
    path("me/", views.MeView.as_view()),
    path("courses/", views.CourseCatalogView.as_view()),
    path("enrollments/", views.EnrollmentView.as_view()),
    path("progress/", views.ProgressView.as_view()),
    path("notifications/", views.NotificationView.as_view()),
    path("quizzes/<uuid:quiz_id>/attempts/", views.StartAttemptView.as_view()),
    path("attempts/<uuid:attempt_id>/answers/", views.AnswerView.as_view()),
    path("attempts/<uuid:attempt_id>/submit/", views.SubmitView.as_view()),
]
