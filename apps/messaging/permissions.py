from django.contrib.auth import get_user_model

from apps.courses.models import CourseRun

User = get_user_model()


def can_access_course_chat(user: User, course_run: CourseRun) -> bool:
    """Return whether a user is a current participant or staff member of a course run."""
    return bool(
        user.is_superuser
        or course_run.enrollments.filter(user=user, status="active").exists()
        or course_run.staff.filter(user=user).exists()
    )
