from django.urls import path

from . import views

urlpatterns = [
    path("courses/<uuid:enrollment_id>/", views.course_learning, name="course-learning"),
    path("blocks/<int:block_id>/complete/", views.complete_block, name="complete-block"),
]
