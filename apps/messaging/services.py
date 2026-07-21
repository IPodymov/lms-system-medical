from collections.abc import Callable
from typing import Any
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from apps.courses.models import CourseRun
from apps.notifications.models import Notification

from .models import CourseMessage, DirectMessage
from .realtime import course_room_name, direct_room_name


def serialize_direct_message(message: DirectMessage) -> dict[str, str | bool | None]:
    return {
        "id": str(message.pk),
        "sender_id": str(message.sender_id),
        "sender_name": message.sender.get_full_name() or message.sender.email,
        "body": message.body,
        "attachment_url": message.attachment.url if message.attachment else None,
        "attachment_content_type": message.attachment_content_type or None,
        "created_at": message.created_at.strftime("%d.%m %H:%M"),
    }


def serialize_course_message(message: CourseMessage) -> dict[str, str | bool | None]:
    return {
        "id": str(message.pk),
        "author_id": str(message.author_id),
        "author_name": message.author.get_full_name() or message.author.email,
        "body": message.body,
        "attachment_url": message.attachment.url if message.attachment else None,
        "attachment_content_type": message.attachment_content_type or None,
        "created_at": message.created_at.strftime("%d.%m %H:%M"),
    }


def _send_after_commit(
    group_name: str, payload: dict[str, str | bool | None]
) -> Callable[[], None]:
    def send() -> None:
        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                group_name, {"type": "chat.message", "message": payload}
            )

    return send


@transaction.atomic
def create_direct_message(
    *,
    sender: Any,
    recipient: Any,
    body: str,
    client_token: UUID,
    attachment: Any = None,
) -> tuple[DirectMessage, bool]:
    """Persist an idempotent direct message and publish it only after commit."""
    message, created = DirectMessage.objects.get_or_create(
        client_token=client_token,
        defaults={
            "sender": sender,
            "recipient": recipient,
            "body": body,
            "attachment": attachment,
            "attachment_content_type": getattr(attachment, "content_type", ""),
        },
    )
    if created:
        Notification.objects.create(
            user=recipient,
            type="direct_message",
            title="Новое личное сообщение",
            body=f"{sender.get_full_name() or sender.email}: {message.body[:120]}",
            payload={"sender_id": str(sender.pk)},
        )
        message = DirectMessage.objects.select_related("sender").get(pk=message.pk)
        transaction.on_commit(
            _send_after_commit(
                direct_room_name(sender.pk, recipient.pk), serialize_direct_message(message)
            )
        )
    return message, created


@transaction.atomic
def create_course_message(
    *,
    course_run: CourseRun,
    author: Any,
    body: str,
    client_token: UUID,
    attachment: Any = None,
) -> tuple[CourseMessage, bool]:
    """Persist an idempotent course message and notify participants after commit."""
    message, created = CourseMessage.objects.get_or_create(
        client_token=client_token,
        defaults={
            "course_run": course_run,
            "author": author,
            "body": body,
            "attachment": attachment,
            "attachment_content_type": getattr(attachment, "content_type", ""),
        },
    )
    if created:
        recipients = course_run.enrollments.filter(status="active").exclude(user=author)
        Notification.objects.bulk_create(
            [
                Notification(
                    user_id=user_id,
                    type="course_chat",
                    title=f"Новое сообщение в чате: {course_run.title}",
                    body=f"{author.get_full_name() or author.email}: {message.body[:120]}",
                    payload={"course_run_id": str(course_run.pk)},
                )
                for user_id in recipients.values_list("user_id", flat=True)
            ]
        )
        message = CourseMessage.objects.select_related("author").get(pk=message.pk)
        transaction.on_commit(
            _send_after_commit(course_room_name(course_run.pk), serialize_course_message(message))
        )
    return message, created
