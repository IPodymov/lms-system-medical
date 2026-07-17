from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify

from apps.assessments.models import Question, QuestionOption, Quiz, QuizQuestion
from apps.assessments.permissions import can_edit_course
from apps.learning.services import EnrollmentError, enroll

from .models import (
    ContentBlock,
    Course,
    CourseAuthor,
    CourseRun,
    CourseSection,
    FileContent,
    Lesson,
)


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
    course = get_object_or_404(Course.objects.prefetch_related("runs"), pk=course_id)
    if course.status != Course.Status.PUBLISHED and not (
        request.user.is_authenticated and can_edit_course(request.user, course)
    ):
        raise PermissionDenied
    return render(
        request,
        "courses/detail.html",
        {
            "course": course,
            "can_edit": request.user.is_authenticated and can_edit_course(request.user, course),
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
            slug = slugify(title) or "course"
            base_slug, index = slug, 2
            while Course.objects.filter(organization=membership.organization, slug=slug).exists():
                slug = f"{base_slug}-{index}"
                index += 1
            course = Course.objects.create(
                organization=membership.organization,
                title=title,
                slug=slug,
                short_description=request.POST.get("short_description", "").strip(),
                description=request.POST.get("description", "").strip(),
                cover=request.FILES.get("cover"),
                created_by=request.user,
            )
            CourseAuthor.objects.create(course=course, user=request.user, role="owner")
            messages.success(request, "Курс создан. Добавьте материалы и тесты.")
            return redirect("course-edit", course.pk)
    return render(request, "courses/create.html")


def _course_lesson(course):
    section, _ = CourseSection.objects.get_or_create(
        course=course,
        position=1,
        defaults={"title": "Учебные материалы", "is_published": True},
    )
    if not section.is_published:
        section.is_published = True
        section.save(update_fields=["is_published"])
    lesson, _ = Lesson.objects.get_or_create(
        section=section,
        position=1,
        defaults={"title": "Материалы и тесты", "is_published": True},
    )
    if not lesson.is_published:
        lesson.is_published = True
        lesson.save(update_fields=["is_published"])
    return lesson


@login_required
def course_edit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if not can_edit_course(request.user, course):
        raise PermissionDenied
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_course":
            course.title = request.POST.get("title", "").strip() or course.title
            course.short_description = request.POST.get("short_description", "").strip()
            course.description = request.POST.get("description", "").strip()
            if request.FILES.get("cover"):
                course.cover = request.FILES["cover"]
            if request.POST.get("status") in dict(Course.Status.choices):
                course.status = request.POST["status"]
                course.published_at = (
                    timezone.now() if course.status == Course.Status.PUBLISHED else None
                )
            course.save()
            messages.success(request, "Данные курса сохранены.")
        elif action == "add_material":
            file = request.FILES.get("file")
            title = request.POST.get("material_title", "").strip()
            if not file or not title:
                messages.error(request, "Укажите название и выберите файл материала.")
            else:
                lesson = _course_lesson(course)
                block = ContentBlock.objects.create(
                    lesson=lesson,
                    type=ContentBlock.Type.FILE,
                    title=title,
                    position=lesson.blocks.count() + 1,
                )
                FileContent.objects.create(
                    content_block=block,
                    file=file,
                    description=request.POST.get("material_description", "").strip(),
                )
                messages.success(request, "Материал загружен.")
        elif action == "add_quiz":
            quiz_title, text = (
                request.POST.get("quiz_title", "").strip(),
                request.POST.get("question_text", "").strip(),
            )
            options = [value.strip() for value in request.POST.getlist("option") if value.strip()]
            try:
                correct = int(request.POST.get("correct_option", ""))
            except ValueError:
                correct = -1
            if not quiz_title or not text or len(options) < 2 or correct not in range(len(options)):
                messages.error(
                    request, "Заполните тест, минимум два варианта и отметьте правильный ответ."
                )
            else:
                with transaction.atomic():
                    lesson = _course_lesson(course)
                    block = ContentBlock.objects.create(
                        lesson=lesson,
                        type=ContentBlock.Type.QUIZ,
                        title=quiz_title,
                        position=lesson.blocks.count() + 1,
                    )
                    quiz = Quiz.objects.create(
                        content_block=block, title=quiz_title, passing_score=100
                    )
                    question = Question.objects.create(
                        organization=course.organization,
                        author=request.user,
                        type=Question.Type.SINGLE,
                        text=text,
                    )
                    for position, option in enumerate(options):
                        QuestionOption.objects.create(
                            question=question,
                            text=option,
                            position=position + 1,
                            is_correct=position == correct,
                        )
                    QuizQuestion.objects.create(quiz=quiz, question=question, position=1)
                messages.success(
                    request, "Тест добавлен. Правильный ответ сохранён только для проверки."
                )
        return redirect("course-edit", course.pk)
    blocks = (
        ContentBlock.objects.filter(lesson__section__course=course)
        .select_related("lesson__section", "file_content", "quiz")
        .order_by("lesson__section__position", "lesson__position", "position")
    )
    return render(request, "courses/edit.html", {"course": course, "blocks": blocks})
