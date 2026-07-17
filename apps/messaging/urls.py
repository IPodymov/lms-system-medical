from django.urls import path

from . import views

urlpatterns = [
    path("", views.direct_messages, name="direct-messages"),
    path("<uuid:user_id>/", views.direct_messages, name="direct-message-thread"),
    path("course/<uuid:run_id>/", views.course_chat, name="course-chat"),
]
