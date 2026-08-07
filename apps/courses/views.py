from datetime import date, datetime, time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.assessments.models import Question
from apps.assessments.permissions import can_edit_course
from apps.imaging import resize_uploaded_image
from apps.learning.models import Enrollment
from apps.learning.selectors import with_block_counts
from apps.learning.services import EnrollmentError, enroll
from apps.organizations.models import Organization

from . import services
from .forms import CourseCreateForm, QuizCreateForm
from .models import (
    ContentBlock,
    Course,
    CourseAuthor,
    CourseEnrollmentLink,
    CourseMaterialLink,
    CourseRun,
    CourseSection,
    Lesson,
)

CATALOG_RUNS_CACHE_KEY = "courses:catalog:published_runs"
CATALOG_RUNS_CACHE_TTL = 60

# Covers are only ever displayed at card size (168px tall); this keeps generous
# headroom for retina/wide layouts while cutting typical multi-MB phone photos
# down dramatically.
COURSE_COVER_MAX_DIMENSION = 1600


def _published_catalog_runs():
    """Active runs of published courses, shown to every visitor identically.

    Cached at the queryset level (not via cache_page) because the rest of the
    catalog page — draft_courses — is specific to the signed-in author and
    must never be served from another visitor's cached page.
    """
    runs = cache.get(CATALOG_RUNS_CACHE_KEY)
    if runs is None:
        runs = list(
            CourseRun.objects.filter(status="active", course__status="published").select_related(
                "course"
            )
        )
        cache.set(CATALOG_RUNS_CACHE_KEY, runs, CATALOG_RUNS_CACHE_TTL)
    return runs


def catalog(request):
    draft_courses = Course.objects.none()
    enrolled_run_ids = set()
    if request.user.is_authenticated:
        draft_courses = (
            Course.objects.filter(status=Course.Status.DRAFT, authors__user=request.user)
            .distinct()
            .order_by("-created_at")
        )
        # Одним запросом, чтобы карточка уже записанного потока не предлагала
        # записаться повторно. Список потоков берётся из общего кэша и не
        # может знать о конкретном посетителе.
        enrolled_run_ids = set(
            Enrollment.objects.filter(user=request.user).values_list("course_run_id", flat=True)
        )
    return render(
        request,
        "courses/catalog.html",
        {
            "runs": _published_catalog_runs(),
            "draft_courses": draft_courses,
            "enrolled_run_ids": enrolled_run_ids,
        },
    )


@login_required
def my_courses(request):
    return render(
        request,
        "courses/my_courses.html",
        {
            "enrollments": with_block_counts(
                request.user.enrollments.select_related("course_run__course")
            )
        },
    )


def course_detail(request, course_id):
    course = get_object_or_404(Course.objects.prefetch_related("runs"), pk=course_id)
    if course.status != Course.Status.PUBLISHED and not (
        request.user.is_authenticated and can_edit_course(request.user, course)
    ):
        raise PermissionDenied
    # Записанному слушателю страница курса нужна как вход в обучение, а не как
    # витрина: показывать ему кнопку записи и рекламное описание — тупик.
    enrollment = None
    if request.user.is_authenticated:
        enrollment = (
            Enrollment.objects.filter(course_run__course=course, user=request.user)
            .select_related("course_run")
            .first()
        )
    return render(
        request,
        "courses/detail.html",
        {
            "course": course,
            "can_edit": request.user.is_authenticated and can_edit_course(request.user, course),
            "enrollment": enrollment,
            "open_run": course.runs.filter(status=CourseRun.Status.ACTIVE).first(),
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
def enroll_by_link(request, link_id):
    enrollment_link = get_object_or_404(
        CourseEnrollmentLink.objects.select_related("course_run"), pk=link_id, is_active=True
    )
    if enrollment_link.expires_at and enrollment_link.expires_at <= timezone.now():
        return render(
            request,
            "components/alert.html",
            {"message": "Срок действия ссылки на курс истёк.", "level": "error"},
            status=400,
        )
    if request.method != "POST":
        return render(request, "courses/enroll_by_link.html", {"enrollment_link": enrollment_link})
    try:
        enroll(course_run=enrollment_link.course_run, user=request.user, source="link")
    except EnrollmentError as error:
        return render(
            request,
            "components/alert.html",
            {"message": str(error), "level": "error"},
            status=400,
        )
    return redirect("my-courses")


def _course_slug(organization, title):
    """Return a unique slug that fits the Course.slug column."""
    max_length = Course._meta.get_field("slug").max_length or 50
    base_slug = (slugify(title) or "course")[:max_length]
    slug, index = base_slug, 2

    while Course.objects.filter(organization=organization, slug=slug).exists():
        suffix = f"-{index}"
        slug = f"{base_slug[: max_length - len(suffix)]}{suffix}"
        index += 1

    return slug


def _parse_course_dates(request):
    start_value = request.POST.get("course_start", "")
    end_value = request.POST.get("course_end", "")
    if not start_value and not end_value:
        return None, None
    if not start_value or not end_value:
        raise ValueError("Укажите и дату начала, и дату окончания обучения.")
    try:
        start_at = timezone.make_aware(datetime.combine(date.fromisoformat(start_value), time.min))
        end_at = timezone.make_aware(datetime.combine(date.fromisoformat(end_value), time.max))
    except ValueError as error:
        raise ValueError("Укажите корректные даты обучения.") from error
    if end_at <= start_at:
        raise ValueError("Дата окончания обучения должна быть позже даты начала.")
    return start_at, end_at


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
    if request.user.is_superuser:
        organization = Organization.objects.filter(is_active=True).order_by("created_at").first()
        if not organization:
            messages.error(request, "Сначала создайте организацию в разделе администрирования.")
            return redirect("admin-dashboard")
    elif membership:
        organization = membership.organization
    else:
        raise PermissionDenied

    form = CourseCreateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        start_at, end_at = form.course_run_period()
        with transaction.atomic():
            course = form.save(commit=False)
            course.organization = organization
            course.slug = _course_slug(organization, course.title)
            course.cover = resize_uploaded_image(
                form.cleaned_data.get("cover"), max_dimension=COURSE_COVER_MAX_DIMENSION
            )
            course.created_by = request.user
            course.save()
            CourseAuthor.objects.create(course=course, user=request.user, role="owner")
            if start_at:
                services.create_course_run(
                    course,
                    request.user,
                    start_at=start_at,
                    end_at=end_at,
                    status=CourseRun.Status.PLANNED,
                )
            _create_initial_material(request, course)
        messages.success(request, "Курс создан. Соберите программу из тем и блоков.")
        return redirect("course-edit", course.pk)

    return render(
        request,
        "courses/create.html",
        {"form": form},
        status=400 if request.method == "POST" else 200,
    )


def _create_initial_material(request, course) -> None:
    """Поддержка старого API формы создания.

    Основной интерфейс ведёт в конструктор, но старые клиенты могли
    передать первый материал прямо в форме создания курса.
    """
    lesson_title = request.POST.get("lesson_title", "").strip()
    lesson_content = request.POST.get("lesson_content", "").strip()
    material = request.FILES.get("material_file")
    if not (lesson_title or lesson_content or material):
        return
    lesson = services.add_lesson(
        course,
        section_title="Программа курса",
        lesson_title=lesson_title or "Введение",
    )
    if lesson_content:
        services.create_text_block(lesson, title=lesson_title or "Введение", body=lesson_content)
    if material:
        services.create_file_block(
            lesson,
            title=request.POST.get("material_title", "").strip() or material.name,
            file=material,
        )


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


def _selected_lesson(course, lesson_id):
    if lesson_id:
        lesson = Lesson.objects.filter(pk=lesson_id, section__course=course).first()
        if lesson:
            return lesson
    return _course_lesson(course)


def _handle_save_course(request, course):
    course.title = request.POST.get("title", "").strip() or course.title
    course.short_description = request.POST.get("short_description", "").strip()
    course.description = request.POST.get("description", "").strip()
    if request.FILES.get("cover"):
        course.cover = resize_uploaded_image(
            request.FILES["cover"], max_dimension=COURSE_COVER_MAX_DIMENSION
        )
    if request.POST.get("status") in dict(Course.Status.choices):
        course.status = request.POST["status"]
        course.published_at = timezone.now() if course.status == Course.Status.PUBLISHED else None
    with transaction.atomic():
        course.save()
        if course.status == Course.Status.PUBLISHED:
            services.ensure_active_course_run(course, request.user)
    if course.status == Course.Status.PUBLISHED:
        messages.success(request, "Курс опубликован и открыт для записи слушателей.")
    else:
        messages.success(request, "Данные курса сохранены.")


def _handle_open_enrollment(request, course):
    with transaction.atomic():
        course.status = Course.Status.PUBLISHED
        course.published_at = course.published_at or timezone.now()
        course.save(update_fields=["status", "published_at"])
        services.ensure_active_course_run(course, request.user)
    messages.success(request, "Курс открыт для записи всех слушателей.")


def _handle_save_schedule(request, course):
    try:
        start_at, end_at = _parse_course_dates(request)
    except ValueError as error:
        messages.error(request, str(error))
        return
    run = (
        course.runs.filter(status=CourseRun.Status.ACTIVE).first()
        or course.runs.filter(status=CourseRun.Status.PLANNED).first()
    )
    if run:
        run.start_at = start_at
        run.end_at = end_at
        run.enrollment_end_at = end_at
        run.save(update_fields=["start_at", "end_at", "enrollment_end_at"])
    else:
        services.create_course_run(
            course, request.user, start_at=start_at, end_at=end_at, status=CourseRun.Status.PLANNED
        )
    messages.success(request, "Сроки обучения сохранены.")


def _handle_enroll_editor(request, course):
    active_run = course.runs.filter(status=CourseRun.Status.ACTIVE).first()
    if not active_run:
        messages.error(request, "Сначала откройте курс для записи.")
        return
    is_already_enrolled = Enrollment.objects.filter(
        course_run=active_run, user=request.user
    ).exists()
    try:
        enroll(course_run=active_run, user=request.user)
    except EnrollmentError as error:
        messages.error(request, str(error))
    else:
        message = (
            "Вы уже добавлены в этот курс." if is_already_enrolled else "Вы добавлены в этот курс."
        )
        messages.success(request, message)


def _handle_add_lesson(request, course):
    section_title = request.POST.get("section_title", "").strip()
    lesson_title = request.POST.get("lesson_title", "").strip()
    if not section_title or not lesson_title:
        messages.error(request, "Укажите раздел и название темы.")
        return
    services.add_lesson(
        course,
        section_title=section_title,
        lesson_title=lesson_title,
        description=request.POST.get("lesson_description", "").strip(),
    )
    messages.success(request, "Тема добавлена.")


def _handle_add_section(request, course):
    section_title = request.POST.get("section_title", "").strip()
    if not section_title:
        messages.error(request, "Укажите название раздела.")
        return
    CourseSection.objects.create(
        course=course,
        title=section_title,
        description=request.POST.get("section_description", "").strip(),
        position=course.sections.count() + 1,
        is_published=True,
    )
    messages.success(request, "Раздел добавлен.")


def _handle_add_material(request, course):
    file = request.FILES.get("file")
    title = request.POST.get("material_title", "").strip()
    if not file or not title:
        messages.error(request, "Укажите название и выберите файл материала.")
        return
    lesson = _selected_lesson(course, request.POST.get("lesson_id"))
    services.create_file_block(
        lesson,
        title=title,
        file=file,
        description=request.POST.get("material_description", "").strip(),
    )
    messages.success(request, "Материал загружен.")


def _handle_add_text(request, course):
    title = request.POST.get("text_title", "").strip()
    body = request.POST.get("text_body", "").strip()
    if not title or not body:
        messages.error(request, "Укажите название и текст лекции.")
        return
    lesson = _selected_lesson(course, request.POST.get("lesson_id"))
    services.create_text_block(lesson, title=title, body=body)
    messages.success(request, "Текст лекции добавлен.")


def _handle_edit_lesson(request, course):
    lesson = get_object_or_404(Lesson, pk=request.POST.get("lesson_id"), section__course=course)
    title = request.POST.get("lesson_title", "").strip()
    if not title:
        messages.error(request, "Укажите название темы.")
        return
    lesson.title = title
    lesson.description = request.POST.get("lesson_description", "").strip()
    lesson.save(update_fields=["title", "description"])
    messages.success(request, "Тема обновлена.")


def _handle_delete_lesson(request, course):
    lesson = get_object_or_404(
        Lesson, pk=request.POST.get("delete_lesson_id"), section__course=course
    )
    section = lesson.section
    lesson.delete()
    services.renumber_positions(section.lessons.order_by("position"))
    messages.success(request, "Тема удалена.")


def _handle_edit_block(request, course):
    block = get_object_or_404(
        ContentBlock, pk=request.POST.get("block_id"), lesson__section__course=course
    )
    title = request.POST.get("block_title", "").strip()
    if not title:
        messages.error(request, "Укажите название блока.")
        return
    with transaction.atomic():
        block.title = title
        block.save(update_fields=["title"])
        if block.type == ContentBlock.Type.TEXT:
            block.text_content.body = request.POST.get("text_body", "").strip()
            block.text_content.save(update_fields=["body"])
        elif block.type == ContentBlock.Type.FILE:
            file_content = block.file_content
            file_content.description = request.POST.get("material_description", "").strip()
            if replacement_file := request.FILES.get("file"):
                file_content.file = replacement_file
                file_content.save(update_fields=["description", "file"])
            else:
                file_content.save(update_fields=["description"])
        elif block.type == ContentBlock.Type.QUIZ:
            block.quiz.title = title
            block.quiz.save(update_fields=["title"])
    messages.success(request, "Блок обновлён.")


def _handle_add_material_link(request, course):
    title = request.POST.get("link_title", "").strip()
    url = request.POST.get("link_url", "").strip()
    if not title or not url:
        messages.error(request, "Укажите название и ссылку на дополнительный материал.")
        return
    CourseMaterialLink.objects.create(
        course=course,
        title=title,
        url=url,
        description=request.POST.get("link_description", "").strip(),
        position=course.material_links.count() + 1,
    )
    messages.success(request, "Ссылка на дополнительный материал добавлена.")


def _handle_add_quiz(request, course):
    # Совместимость с прежней формой редактора и API-клиентами.
    quiz_title = request.POST.get("quiz_title", "").strip()
    text = request.POST.get("question_text", "").strip()
    options = [value.strip() for value in request.POST.getlist("option") if value.strip()]
    try:
        correct = int(request.POST.get("correct_option", ""))
    except ValueError:
        correct = -1
    if not quiz_title or not text or len(options) < 2 or correct not in range(len(options)):
        messages.error(request, "Заполните тест, минимум два варианта и отметьте правильный ответ.")
        return
    lesson = _selected_lesson(course, request.POST.get("lesson_id"))
    services.create_quiz_block(
        lesson,
        title=quiz_title,
        question_text=text,
        options=options,
        correct_indexes={correct},
        organization=course.organization,
        author=request.user,
    )
    messages.success(request, "Тест добавлен в программу курса.")


def _handle_delete_block(request, course):
    block = get_object_or_404(
        ContentBlock, pk=request.POST.get("delete_block_id"), lesson__section__course=course
    )
    lesson = block.lesson
    block.delete()
    services.renumber_positions(lesson.blocks.order_by("position"))
    messages.success(request, "Блок удалён.")


def _handle_reorder_blocks(request, course):
    lesson = get_object_or_404(Lesson, pk=request.POST.get("lesson_id"), section__course=course)
    block_ids = request.POST.getlist("block_id")
    blocks = {
        str(block.pk): block
        for block in ContentBlock.objects.filter(pk__in=block_ids, lesson=lesson)
    }
    if set(block_ids) != set(blocks) or len(block_ids) != lesson.blocks.count():
        messages.error(request, "Не удалось сохранить порядок блоков.")
        return
    services.reorder(blocks, block_ids)
    messages.success(request, "Порядок блоков сохранён.")


def _handle_reorder_lessons(request, course):
    section = get_object_or_404(CourseSection, pk=request.POST.get("section_id"), course=course)
    lesson_ids = request.POST.getlist("lesson_id")
    lessons = {
        str(lesson.pk): lesson
        for lesson in Lesson.objects.filter(pk__in=lesson_ids, section=section)
    }
    if set(lesson_ids) != set(lessons) or len(lesson_ids) != section.lessons.count():
        messages.error(request, "Не удалось сохранить порядок тем.")
        return
    services.reorder(lessons, lesson_ids)
    messages.success(request, "Порядок тем сохранён.")


def _move_within(items: list, moved, direction: str) -> list | None:
    """Список id соседей с переставленным на шаг элементом.

    None означает, что двигать некуда: элемент уже первый или последний.
    """
    ids = [str(item.pk) for item in items]
    index = ids.index(str(moved.pk))
    target = index - 1 if direction == "up" else index + 1
    if not 0 <= target < len(ids):
        return None
    ids[index], ids[target] = ids[target], ids[index]
    return ids


def _handle_move_lesson(request, course):
    """Переставить тему на шаг вверх или вниз.

    Обязательная альтернатива перетаскиванию: WCAG 2.5.7 требует, чтобы
    любое действие, доступное одним указателем, выполнялось и без него.
    Работает без JavaScript — это обычная отправка формы.
    """
    lesson = get_object_or_404(Lesson, pk=request.POST.get("lesson_id"), section__course=course)
    siblings = list(lesson.section.lessons.all())
    ordered_ids = _move_within(siblings, lesson, request.POST.get("direction"))
    if ordered_ids is None:
        return None
    services.reorder({str(item.pk): item for item in siblings}, ordered_ids)
    messages.success(request, "Порядок тем сохранён.")
    return f"lesson-{lesson.pk}"


def _handle_move_block(request, course):
    """То же для учебного блока внутри темы."""
    block = get_object_or_404(
        ContentBlock, pk=request.POST.get("block_id"), lesson__section__course=course
    )
    siblings = list(block.lesson.blocks.all())
    ordered_ids = _move_within(siblings, block, request.POST.get("direction"))
    if ordered_ids is None:
        return None
    services.reorder({str(item.pk): item for item in siblings}, ordered_ids)
    messages.success(request, "Порядок блоков сохранён.")
    return f"block-{block.pk}"


_COURSE_EDIT_ACTIONS = {
    "save_course": _handle_save_course,
    "open_enrollment": _handle_open_enrollment,
    "save_schedule": _handle_save_schedule,
    "enroll_editor": _handle_enroll_editor,
    "add_lesson": _handle_add_lesson,
    "add_section": _handle_add_section,
    "add_material": _handle_add_material,
    "add_text": _handle_add_text,
    "edit_lesson": _handle_edit_lesson,
    "delete_lesson": _handle_delete_lesson,
    "edit_block": _handle_edit_block,
    "add_material_link": _handle_add_material_link,
    "add_quiz": _handle_add_quiz,
    "delete_block": _handle_delete_block,
    "reorder_blocks": _handle_reorder_blocks,
    "reorder_lessons": _handle_reorder_lessons,
    "move_lesson": _handle_move_lesson,
    "move_block": _handle_move_block,
}


@login_required
def course_edit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if not can_edit_course(request.user, course):
        raise PermissionDenied
    if request.method == "POST":
        handler = _COURSE_EDIT_ACTIONS.get(request.POST.get("action"))
        # Обработчик может вернуть якорь: после перестановки страница должна
        # открыться на переставленном элементе, а не уехать в начало.
        anchor = handler(request, course) if handler else None
        url = reverse("course-edit", args=[course.pk])
        return redirect(f"{url}#{anchor}" if anchor else url)
    blocks = (
        ContentBlock.objects.filter(lesson__section__course=course)
        .select_related("lesson__section", "file_content", "quiz")
        .order_by("lesson__section__position", "lesson__position", "position")
    )
    active_run = course.runs.filter(status=CourseRun.Status.ACTIVE).first()
    schedule_run = active_run or course.runs.filter(status=CourseRun.Status.PLANNED).first()
    return render(
        request,
        "courses/edit.html",
        {
            "course": course,
            "blocks": blocks,
            "lessons": Lesson.objects.filter(section__course=course).select_related("section"),
            "sections": course.sections.prefetch_related("lessons__blocks"),
            "material_links": course.material_links.all(),
            "active_run": active_run,
            "schedule_run": schedule_run,
            "is_editor_enrolled": (
                active_run is not None
                and Enrollment.objects.filter(course_run=active_run, user=request.user).exists()
            ),
        },
    )


@login_required
def quiz_create(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if not can_edit_course(request.user, course):
        raise PermissionDenied
    lessons = Lesson.objects.filter(section__course=course).select_related("section")
    selected_lesson = _selected_lesson(course, request.GET.get("lesson_id"))
    form = QuizCreateForm(
        request.POST or None,
        request.FILES or None,
        lessons=lessons,
        initial={"lesson": selected_lesson},
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        services.create_quiz_block(
            data["lesson"] or _selected_lesson(course, None),
            title=data["quiz_title"],
            question_text=data["question_text"],
            options=data["options"],
            correct_indexes=data["correct_indexes"],
            organization=course.organization,
            author=request.user,
            question_type=(
                Question.Type.MULTIPLE
                if data["answer_mode"] == "multiple"
                else Question.Type.SINGLE
            ),
            image=data["question_image"] if form.is_image_question else None,
            markers=data["markers"] if form.is_image_question else None,
        )
        messages.success(request, "Тест добавлен в программу курса.")
        return redirect("course-edit", course.pk)
    return render(
        request,
        "courses/quiz_create.html",
        {"course": course, "form": form},
        status=400 if request.method == "POST" else 200,
    )
