from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.Login.as_view(), name="login"),
    path("register/", views.register, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("documentation/", views.documentation_home, name="documentation-home"),
    path("documentation/courses/", views.course_documentation, name="documentation-courses"),
    path(
        "documentation/management/",
        views.management_documentation,
        name="documentation-management",
    ),
    path("management/", views.admin_dashboard, name="admin-dashboard"),
    path(
        "management/documentation/<str:token>/",
        views.admin_documentation,
        name="admin-documentation",
    ),
    path("management/organizations/add/", views.add_organization, name="add-organization"),
    path("management/users/add/", views.add_user, name="add-user"),
    path("management/teachers/add/", views.add_teacher, name="add-teacher"),
    path("management/groups/add/", views.add_study_group, name="add-study-group"),
    path("management/groups/<int:group_id>/", views.study_group_detail, name="study-group-detail"),
    path("management/students/add/", views.add_student, name="add-student"),
    path("management/students/import/", views.import_students, name="import-students"),
    path("management/course-staff/assign/", views.assign_course_staff, name="assign-course-staff"),
    path(
        "management/course-staff/<int:staff_id>/remove/",
        views.remove_course_staff,
        name="remove-course-staff",
    ),
    path(
        "management/enrollments/",
        views.manage_course_enrollment,
        name="manage-course-enrollment",
    ),
    path(
        "management/enrollment-links/create/",
        views.create_course_enrollment_link,
        name="create-course-enrollment-link",
    ),
    path(
        "management/enrollment-links/<uuid:link_id>/deactivate/",
        views.deactivate_course_enrollment_link,
        name="deactivate-course-enrollment-link",
    ),
    path(
        "management/users/<int:membership_id>/role/",
        views.manage_user_role,
        name="manage-user-role",
    ),
]
