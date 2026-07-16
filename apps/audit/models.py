from django.conf import settings
from django.db import models
from apps.accounts.models import TimeStampedModel, UUIDModel
from apps.organizations.models import Organization


class AuditLog(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=64)
    entity_type = models.CharField(max_length=128)
    entity_id = models.UUIDField(null=True)
    old_data = models.JSONField(default=dict, blank=True)
    new_data = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
