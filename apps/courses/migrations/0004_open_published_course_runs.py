from datetime import timedelta

from django.db import migrations
from django.utils import timezone


def create_active_runs_for_published_courses(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    CourseRun = apps.get_model("courses", "CourseRun")
    CourseRunStaff = apps.get_model("courses", "CourseRunStaff")
    now = timezone.now()
    academic_year = f"{now.year}/{now.year + 1}"

    for course in Course.objects.filter(status="published").iterator():
        if CourseRun.objects.filter(course_id=course.pk, status="active").exists():
            continue
        run = CourseRun.objects.create(
            course_id=course.pk,
            title=f"{course.title} — основной поток",
            semester="Открытый",
            academic_year=academic_year,
            start_at=now,
            end_at=now + timedelta(days=365),
            enrollment_start_at=now,
            enrollment_end_at=now + timedelta(days=365),
            status="active",
        )
        CourseRunStaff.objects.get_or_create(
            course_run_id=run.pk,
            user_id=course.created_by_id,
            defaults={"role": "teacher"},
        )


class Migration(migrations.Migration):
    dependencies = [("courses", "0003_coursemateriallink")]

    operations = [migrations.RunPython(create_active_runs_for_published_courses, migrations.RunPython.noop)]
