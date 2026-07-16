from django.urls import path
from . import views
urlpatterns=[path("catalog/",views.catalog,name="course-catalog"),path("mine/",views.my_courses,name="my-courses"),path("<uuid:course_id>/",views.course_detail,name="course-detail"),path("runs/<uuid:run_id>/enroll/",views.enroll_view,name="enroll"),path("create/",views.course_create,name="course-create")]
