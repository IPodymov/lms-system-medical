from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from .models import Course, CourseAuthor, CourseRun
from apps.assessments.permissions import can_edit_course
from apps.learning.services import EnrollmentError, enroll


def catalog(request):
    return render(
        request,
        "courses/catalog.html",
        {
            "runs": CourseRun.objects.filter(
                status="active", course__status="published"
            ).select_related("course")
        },
    )


@login_required
def my_courses(request):
    return render(
        request,
        "courses/my_courses.html",
        {"enrollments": request.user.enrollments.select_related("course_run__course")},
    )


def course_detail(request, course_id):
    return render(
        request,
        "courses/detail.html",
        {
            "course": get_object_or_404(
                Course.objects.prefetch_related("runs"),
                pk=course_id,
                status="published",
            )
        },
    )


@login_required
def enroll_view(request, run_id):
    if request.method != "POST":
        return redirect("course-catalog")
    try:
        enroll(course_run=get_object_or_404(CourseRun, pk=run_id), user=request.user)
    except EnrollmentError as error:
        return render(
            request,
            "components/alert.html",
            {"message": str(error), "level": "error"},
            status=400,
        )
    return redirect("my-courses")


@login_required
def course_create(request):
    membership = (
        request.user.memberships.filter(
            role__in=["teacher", "assistant", "organization_admin", "system_admin"],
            status="active",
        )
        .select_related("organization")
        .first()
    )
    if not membership:
        raise PermissionDenied

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        if title:
            course = Course.objects.create(
                organization=membership.organization,
                title=title,
                slug=slugify(title),
                created_by=request.user,
            )
            CourseAuthor.objects.create(course=course, user=request.user, role="owner")
            return redirect("course-detail", course.pk)
    return render(request, "courses/create.html")
