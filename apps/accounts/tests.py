from django.test import TestCase
from django.urls import reverse

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
