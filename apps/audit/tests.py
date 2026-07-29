from django.test import TestCase

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.organizations.models import Organization
from apps.test_helpers import CourseFixture


class AuditLogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.data = CourseFixture.create(email="audit@test.local")

    def test_audit_log_keeps_actor_and_json_snapshots(self):
        item = AuditLog.objects.create(
            organization=self.data["organization"],
            actor=self.data["user"],
            action="course.updated",
            entity_type="Course",
            entity_id=self.data["course"].pk,
            old_data={"status": "draft"},
            new_data={"status": "published"},
            ip_address="127.0.0.1",
        )
        item.refresh_from_db()
        self.assertEqual(item.actor_id, self.data["user"].pk)
        self.assertEqual(item.old_data["status"], "draft")
        self.assertEqual(item.new_data["status"], "published")

    def test_audit_log_can_survive_deleted_actor_and_organization(self):
        user = User.objects.create_user("orphan-audit@test.local", "pass")
        organization = Organization.objects.create(
            name="Временная организация", short_name="ВО", slug="temporary-audit-org"
        )
        item = AuditLog.objects.create(
            organization=organization,
            actor=user,
            action="course.deleted",
            entity_type="Course",
        )
        user.delete()
        organization.delete()
        item.refresh_from_db()
        self.assertIsNone(item.actor_id)
        self.assertIsNone(item.organization_id)
