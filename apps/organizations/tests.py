from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.courses.models import Course

from .models import Organization, OrganizationMembership


class OrganizationManagementTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser("admin@example.test", "safe-password-123")
        self.client.force_login(self.superuser)

    def test_superuser_can_open_management_without_organizations(self):
        response = self.client.get(reverse("admin-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Создать организацию")

    def test_superuser_can_create_college_organization(self):
        response = self.client.post(
            reverse("add-organization"),
            {
                "name": "Медицинский колледж",
                "short_name": "Медколледж",
                "institution_type": Organization.InstitutionType.COLLEGE,
            },
        )

        organization = Organization.objects.get(name="Медицинский колледж")
        self.assertRedirects(response, reverse("admin-dashboard"))
        self.assertEqual(organization.institution_type, Organization.InstitutionType.COLLEGE)
        self.assertTrue(
            OrganizationMembership.objects.filter(
                organization=organization,
                user=self.superuser,
                role=OrganizationMembership.Role.SYSTEM_ADMIN,
            ).exists()
        )

    def test_superuser_can_create_a_course_after_creating_an_organization(self):
        self.client.post(
            reverse("add-organization"),
            {
                "name": "Медицинский университет",
                "short_name": "МедУниверситет",
                "institution_type": Organization.InstitutionType.UNIVERSITY,
            },
        )

        response = self.client.post(reverse("course-create"), {"title": "Анатомия"})

        course = Course.objects.get(title="Анатомия")
        self.assertRedirects(response, reverse("course-edit", args=[course.pk]))
        self.assertEqual(
            course.organization.institution_type,
            Organization.InstitutionType.UNIVERSITY,
        )
        self.assertTrue(course.authors.filter(user=self.superuser, role="owner").exists())
