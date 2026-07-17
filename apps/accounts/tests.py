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
