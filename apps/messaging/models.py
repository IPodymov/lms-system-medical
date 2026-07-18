import uuid

from django.conf import settings
from django.db import models

from apps.accounts.models import TimeStampedModel, UUIDModel
from apps.courses.models import CourseRun


class FavoriteContact(models.Model):
    """A user-selected contact that stays visible before a dialogue starts."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_contacts"
    )
    contact = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "contact"], name="unique_favorite_contact")
        ]


class DirectMessage(UUIDModel, TimeStampedModel):
    """A private message between two LMS users."""

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_messages",
    )
    body = models.TextField(max_length=4000, blank=True)
    attachment = models.FileField(upload_to="message_attachments/", blank=True)
    attachment_content_type = models.CharField(max_length=100, blank=True)
    client_token = models.UUIDField(unique=True, default=uuid.uuid4)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["sender", "recipient", "created_at"]),
            models.Index(fields=["recipient", "is_read"]),
        ]


class CourseMessage(UUIDModel, TimeStampedModel):
    """Common chat for a particular course run."""

    course_run = models.ForeignKey(
        CourseRun, on_delete=models.CASCADE, related_name="chat_messages"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_messages",
    )
    body = models.TextField(max_length=4000, blank=True)
    attachment = models.FileField(upload_to="message_attachments/", blank=True)
    attachment_content_type = models.CharField(max_length=100, blank=True)
    client_token = models.UUIDField(unique=True, default=uuid.uuid4)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["course_run", "created_at"])]
