from django.conf import settings
from django.db import models
from apps.accounts.models import TimeStampedModel, UUIDModel
class Notification(UUIDModel, TimeStampedModel):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="notifications"); type=models.CharField(max_length=64); title=models.CharField(max_length=255); body=models.TextField(); payload=models.JSONField(default=dict,blank=True); is_read=models.BooleanField(default=False); read_at=models.DateTimeField(null=True,blank=True)
    class Meta: indexes=[models.Index(fields=["user","is_read","created_at"])]
