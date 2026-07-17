from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.assessments.models import Question, QuestionOption, Quiz, QuizQuestion
from apps.courses.models import (
    ContentBlock,
    Course,
    CourseAuthor,
    CourseRun,
    CourseRunStaff,
    CourseSection,
    Lesson,
    TextContent,
)
from apps.learning.models import Enrollment
from apps.organizations.models import (
    Department,
    Faculty,
    Organization,
    OrganizationMembership,
    StudyGroup,
)


class Command(BaseCommand):
    help = "Создаёт идемпотентные демонстрационные данные"

    def handle(self, *args, **kwargs):
        org, _ = Organization.objects.get_or_create(
            slug="med-university",
            defaults={"name": "Медицинский университет", "short_name": "МедУниверситет"},
        )
        faculty, _ = Faculty.objects.get_or_create(
            organization=org, code="MED", defaults={"name": "Лечебный факультет"}
        )
        department, _ = Department.objects.get_or_create(
            faculty=faculty, code="THER", defaults={"name": "Кафедра терапии"}
        )
        StudyGroup.objects.get_or_create(
            department=department,
            name="Л-101",
            admission_year=2025,
            defaults={"graduation_year": 2031},
        )
        users = []
        for email, first, last, role in [
            ("admin@demo.local", "Админ", "Системный", "system_admin"),
            ("teacher@demo.local", "Анна", "Преподаватель", "teacher"),
            ("student1@demo.local", "Иван", "Студент", "student"),
            ("student2@demo.local", "Мария", "Студентка", "student"),
        ]:
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email,
                    "first_name": first,
                    "last_name": last,
                    "is_staff": role == "system_admin",
                    "is_superuser": role == "system_admin",
                },
            )
            user.set_password("demo12345")
            user.save()
            OrganizationMembership.objects.get_or_create(
                organization=org, user=user, defaults={"role": role}
            )
            users.append(user)
        admin, teacher, s1, s2 = users
        course, _ = Course.objects.get_or_create(
            organization=org,
            slug="clinical-thinking",
            defaults={
                "title": "Основы клинического мышления",
                "short_description": "Вводный курс для студентов-медиков.",
                "description": "Демонстрационный курс.",
                "status": "published",
                "created_by": teacher,
                "published_at": timezone.now(),
            },
        )
        CourseAuthor.objects.get_or_create(course=course, user=teacher, defaults={"role": "owner"})
        now = timezone.now()
        run, _ = CourseRun.objects.get_or_create(
            course=course,
            academic_year="2026/2027",
            semester="Осень",
            defaults={
                "title": "Основы клинического мышления — осень",
                "start_at": now - timedelta(days=7),
                "end_at": now + timedelta(days=90),
                "enrollment_start_at": now - timedelta(days=14),
                "enrollment_end_at": now + timedelta(days=30),
                "status": "active",
                "max_students": 100,
            },
        )
        CourseRunStaff.objects.get_or_create(
            course_run=run, user=teacher, defaults={"role": "teacher"}
        )
        section, _ = CourseSection.objects.get_or_create(
            course=course, position=1, defaults={"title": "Введение", "is_published": True}
        )
        lesson, _ = Lesson.objects.get_or_create(
            section=section,
            position=1,
            defaults={
                "title": "Клиническое мышление",
                "is_published": True,
                "estimated_duration_minutes": 20,
            },
        )
        block, _ = ContentBlock.objects.get_or_create(
            lesson=lesson,
            position=1,
            defaults={"type": "text", "title": "Материал", "is_required": True},
        )
        TextContent.objects.get_or_create(
            content_block=block,
            defaults={"body": "Клиническое мышление начинается с внимательного сбора данных."},
        )
        quiz_block, _ = ContentBlock.objects.get_or_create(
            lesson=lesson,
            position=2,
            defaults={"type": "quiz", "title": "Проверка знаний", "is_required": True},
        )
        quiz, _ = Quiz.objects.get_or_create(
            content_block=quiz_block,
            defaults={"title": "Мини-тест", "attempt_limit": 2, "passing_score": 50},
        )
        question, _ = Question.objects.get_or_create(
            organization=org,
            author=teacher,
            text="Что важно в начале клинического разбора?",
            defaults={"type": "single_choice"},
        )
        QuestionOption.objects.get_or_create(
            question=question, position=1, defaults={"text": "Сбор анамнеза", "is_correct": True}
        )
        QuestionOption.objects.get_or_create(
            question=question,
            position=2,
            defaults={"text": "Сразу назначить лечение", "is_correct": False},
        )
        QuizQuestion.objects.get_or_create(
            quiz=quiz, question=question, defaults={"position": 1, "points": 1}
        )
        for student in (s1, s2):
            Enrollment.objects.get_or_create(
                course_run=run,
                user=student,
                defaults={"status": "active", "enrollment_source": "manual"},
            )
        self.stdout.write(
            self.style.SUCCESS("Demo-данные созданы. Пароль всех пользователей: demo12345")
        )
