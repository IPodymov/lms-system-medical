from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.courses.models import Course, CourseRun, CourseRunStaff
from apps.learning.models import Enrollment
from apps.organizations.models import (
    Department,
    Faculty,
    Organization,
    OrganizationMembership,
    StudyGroup,
    StudyGroupMember,
)

from .models import User


class RegistrationViewTests(TestCase):
    def test_user_can_register_and_is_logged_in(self):
        response = self.client.post(
            reverse("register"),
            {
                "first_name": "Анна",
                "last_name": "Иванова",
                "email": "anna@example.test",
                "password1": "safe-password-123",
                "password2": "safe-password-123",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        user = User.objects.get(email="anna@example.test")
        self.assertEqual(user.username, user.email)
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user("anna@example.test", "safe-password-123")

        response = self.client.post(
            reverse("register"),
            {
                "email": "anna@example.test",
                "password1": "safe-password-123",
                "password2": "safe-password-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Пользователь с таким email уже зарегистрирован.")


class AdminDocumentationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin@example.test", "safe-password-123")
        self.other_admin = User.objects.create_superuser(
            "second-admin@example.test", "safe-password-123"
        )

    def test_signed_documentation_url_is_available_to_its_admin_only(self):
        self.client.force_login(self.admin)
        dashboard = self.client.get(reverse("admin-dashboard"))
        documentation_url = dashboard.context["admin_documentation_url"]

        response = self.client.get(documentation_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Документация администратора")

        self.client.force_login(self.other_admin)
        response = self.client.get(documentation_url)

        self.assertEqual(response.status_code, 403)


class NavigationTests(TestCase):
    def test_student_does_not_see_course_creation_and_full_name_includes_patronymic(self):
        student = User.objects.create_user(
            "student@example.test",
            "safe-password-123",
            first_name="Иван",
            last_name="Петров",
            middle_name="Сергеевич",
        )
        self.client.force_login(student)

        response = self.client.get(reverse("dashboard"))

        self.assertNotContains(response, 'href="/courses/create/"')
        self.assertContains(response, "Петров Иван Сергеевич")

    def test_teacher_sees_course_creation(self):
        teacher = User.objects.create_user("teacher@example.test", "safe-password-123")
        organization = Organization.objects.create(
            name="Медицинский университет", short_name="МУ", slug="medical-university"
        )
        OrganizationMembership.objects.create(
            user=teacher,
            organization=organization,
            role=OrganizationMembership.Role.TEACHER,
        )
        self.client.force_login(teacher)

        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, 'href="/courses/create/"')
        self.assertContains(response, reverse("documentation-home"))
        self.assertEqual(self.client.get(reverse("documentation-courses")).status_code, 200)
        self.assertEqual(self.client.get(reverse("documentation-management")).status_code, 403)

    def test_student_cannot_see_or_open_documentation(self):
        student = User.objects.create_user("student@example.test", "safe-password-123")
        self.client.force_login(student)

        response = self.client.get(reverse("dashboard"))

        self.assertNotContains(response, reverse("documentation-home"))
        self.assertEqual(self.client.get(reverse("documentation-home")).status_code, 403)

    def test_organization_admin_can_open_management_documentation(self):
        admin = User.objects.create_user("org-admin@example.test", "safe-password-123")
        organization = Organization.objects.create(
            name="Медицинский университет", short_name="МУ", slug="medical-university"
        )
        OrganizationMembership.objects.create(
            user=admin,
            organization=organization,
            role=OrganizationMembership.Role.ORGANIZATION_ADMIN,
        )
        self.client.force_login(admin)

        self.assertEqual(self.client.get(reverse("documentation-home")).status_code, 200)
        self.assertEqual(self.client.get(reverse("documentation-management")).status_code, 200)


class CollegeManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin@example.test", "safe-password-123")
        self.organization = Organization.objects.create(
            name="Медицинский колледж", short_name="МК", slug="medical-college"
        )
        self.client.force_login(self.admin)

    def test_excel_import_creates_group_student_and_membership(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from openpyxl import Workbook

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["group", "email", "password", "first_name", "last_name"])
        worksheet.append(["С-21", "student@example.test", "safe-password-123", "Иван", "Петров"])
        content = BytesIO()
        workbook.save(content)

        response = self.client.post(
            reverse("import-students"),
            {
                "organization_id": self.organization.pk,
                "spreadsheet": SimpleUploadedFile(
                    "students.xlsx",
                    content.getvalue(),
                    content_type=(
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ),
                ),
            },
        )

        self.assertRedirects(response, reverse("admin-dashboard"))
        student = User.objects.get(email="student@example.test")
        membership = OrganizationMembership.objects.get(
            user=student, organization=self.organization
        )
        self.assertEqual(membership.role, OrganizationMembership.Role.STUDENT)
        self.assertTrue(student.studygroupmember_set.filter(study_group__name="С-21").exists())

    def test_excel_import_generates_credentials_from_group_and_full_name(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from openpyxl import Workbook

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["group", "full_name"])
        worksheet.append(["С-22", "Петров Иван Сергеевич"])
        content = BytesIO()
        workbook.save(content)

        response = self.client.post(
            reverse("import-students"),
            {
                "organization_id": self.organization.pk,
                "spreadsheet": SimpleUploadedFile("students.xlsx", content.getvalue()),
            },
        )

        student = User.objects.get(last_name="Петров", first_name="Иван")
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(student.username.startswith("student-"))
        self.assertEqual(student.email, f"{student.username}@import.local")
        self.assertTrue(student.studygroupmember_set.filter(study_group__name="С-22").exists())

    def test_admin_can_assign_curator_and_manage_enrollment(self):
        teacher = User.objects.create_user("teacher@example.test", "safe-password-123")
        student = User.objects.create_user("student@example.test", "safe-password-123")
        OrganizationMembership.objects.create(
            user=teacher,
            organization=self.organization,
            role=OrganizationMembership.Role.TEACHER,
        )
        OrganizationMembership.objects.create(
            user=student,
            organization=self.organization,
            role=OrganizationMembership.Role.STUDENT,
        )
        course = Course.objects.create(
            organization=self.organization,
            title="Анатомия",
            slug="anatomy",
            created_by=self.admin,
        )
        now = timezone.now()
        course_run = CourseRun.objects.create(
            course=course,
            title="Основной поток",
            semester="1",
            academic_year="2026",
            start_at=now,
            end_at=now,
            enrollment_start_at=now,
            enrollment_end_at=now,
            status=CourseRun.Status.ACTIVE,
        )

        self.client.post(
            reverse("assign-course-staff"),
            {"course_run_id": course_run.pk, "user_id": teacher.pk, "role": "curator"},
        )
        self.client.post(
            reverse("manage-course-enrollment"),
            {"action": "add_student", "course_run_id": course_run.pk, "user_id": student.pk},
        )

        self.assertTrue(
            CourseRunStaff.objects.filter(
                course_run=course_run, user=teacher, role="curator"
            ).exists()
        )
        self.assertTrue(Enrollment.objects.filter(course_run=course_run, user=student).exists())

    def test_group_page_enrolls_all_active_members(self):
        faculty = Faculty.objects.create(
            organization=self.organization, name="Общее", code="general"
        )
        department = Department.objects.create(faculty=faculty, name="Общее", code="general")
        group = StudyGroup.objects.create(
            department=department, name="С-24", admission_year=2026, graduation_year=2030
        )
        student = User.objects.create_user("student@example.test", "safe-password-123")
        OrganizationMembership.objects.create(
            user=student,
            organization=self.organization,
            role=OrganizationMembership.Role.STUDENT,
        )
        StudyGroupMember.objects.create(study_group=group, user=student)
        course = Course.objects.create(
            organization=self.organization,
            title="Анатомия",
            slug="anatomy",
            created_by=self.admin,
        )
        now = timezone.now()
        course_run = CourseRun.objects.create(
            course=course,
            title="Основной поток",
            semester="1",
            academic_year="2026",
            start_at=now,
            end_at=now,
            enrollment_start_at=now,
            enrollment_end_at=now,
            status=CourseRun.Status.ACTIVE,
        )

        response = self.client.post(
            reverse("manage-course-enrollment"),
            {"action": "add_group", "course_run_id": course_run.pk, "group_id": group.pk},
        )

        self.assertRedirects(response, reverse("admin-dashboard"))
        self.assertTrue(Enrollment.objects.filter(course_run=course_run, user=student).exists())
        detail = self.client.get(reverse("study-group-detail", args=[group.pk]))
        self.assertContains(detail, student.email)
