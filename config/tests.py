from importlib import reload

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import Resolver404, clear_url_caches, resolve

import config.urls
from apps.accounts.models import User


class AdminUrlTests(SimpleTestCase):
    def _reload_urls(self):
        clear_url_caches()
        reload(config.urls)
        self.addCleanup(clear_url_caches)
        self.addCleanup(reload, config.urls)

    @override_settings(ADMIN_URL="admin/")
    def test_admin_is_available_at_default_debug_url(self):
        self._reload_urls()

        self.assertEqual(resolve("/admin/").namespace, "admin")

    @override_settings(ADMIN_URL="control-4f6d8a92/")
    def test_admin_is_available_at_configured_private_url(self):
        self._reload_urls()

        self.assertEqual(resolve("/control-4f6d8a92/").namespace, "admin")

    @override_settings(ADMIN_URL="")
    def test_admin_is_not_routed_without_production_url(self):
        self._reload_urls()

        with self.assertRaises(Resolver404):
            resolve("/admin/")


class AdminAccessTests(TestCase):
    @override_settings(ADMIN_URL="admin/")
    def test_superuser_can_open_admin_in_debug_mode(self):
        user = User.objects.create_superuser("admin@example.test", "safe-password-123")
        clear_url_caches()
        reload(config.urls)
        self.addCleanup(clear_url_caches)
        self.addCleanup(reload, config.urls)

        self.client.force_login(user)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
