from abc import ABC, abstractmethod
from uuid import UUID, uuid4

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.courses.models import CourseRun

from .permissions import can_access_course_chat
from .realtime import course_room_name, direct_room_name
from .services import create_course_message, create_direct_message

User = get_user_model()


class BaseChatConsumer(JsonWebsocketConsumer, ABC):
    max_message_length = 4000
    room_group_name: str

    @abstractmethod
    def set_chat_context(self) -> bool:
        """Set the authorized room context before accepting the connection."""

    @abstractmethod
    def create_message(self, *, body: str, client_token: UUID) -> None:
        """Persist and publish a message for the established room context."""

    def connect(self) -> None:
        if not self.scope["user"].is_authenticated:
            self.close(code=4401)
            return
        if not self.set_chat_context():
            self.close(code=4403)
            return
        async_to_sync(self.channel_layer.group_add)(self.room_group_name, self.channel_name)
        self.accept()

    def disconnect(self, code: int) -> None:
        _ = code
        if hasattr(self, "room_group_name"):
            async_to_sync(self.channel_layer.group_discard)(self.room_group_name, self.channel_name)

    def receive_json(self, content: dict, **kwargs: object) -> None:
        if not self.can_send():
            self.close(code=4403)
            return
        body = str(content.get("body", "")).strip()
        if not body or len(body) > self.max_message_length:
            self.send_json(
                {
                    "type": "error",
                    "detail": "Введите сообщение длиной до 4000 символов.",
                }
            )
            return
        try:
            client_token = UUID(str(content.get("client_token")))
        except (TypeError, ValueError, ValidationError):
            client_token = uuid4()
        self.create_message(body=body, client_token=client_token)

    def chat_message(self, event: dict) -> None:
        self.send_json({"type": "message", "message": event["message"]})

    def can_send(self) -> bool:
        return bool(self.scope["user"].is_active)


class DirectChatConsumer(BaseChatConsumer):
    recipient: User

    def set_chat_context(self) -> bool:
        try:
            recipient_id = UUID(str(self.scope["url_route"]["kwargs"]["user_id"]))
        except (KeyError, TypeError, ValueError):
            return False
        self.recipient = User.objects.filter(pk=recipient_id, is_active=True).first()
        if self.recipient is None or self.recipient == self.scope["user"]:
            return False
        self.room_group_name = direct_room_name(self.scope["user"].pk, self.recipient.pk)
        return True

    def create_message(self, *, body: str, client_token: UUID) -> None:
        create_direct_message(
            sender=self.scope["user"],
            recipient=self.recipient,
            body=body,
            client_token=client_token,
        )

    def can_send(self) -> bool:
        return (
            User.objects.filter(pk=self.scope["user"].pk, is_active=True).exists()
            and User.objects.filter(pk=self.recipient.pk, is_active=True).exists()
        )


class CourseChatConsumer(BaseChatConsumer):
    course_run: CourseRun

    def set_chat_context(self) -> bool:
        try:
            course_run_id = UUID(str(self.scope["url_route"]["kwargs"]["run_id"]))
        except (KeyError, TypeError, ValueError):
            return False
        self.course_run = CourseRun.objects.filter(pk=course_run_id).first()
        if self.course_run is None or not can_access_course_chat(
            self.scope["user"], self.course_run
        ):
            return False
        self.room_group_name = course_room_name(self.course_run.pk)
        return True

    def create_message(self, *, body: str, client_token: UUID) -> None:
        create_course_message(
            course_run=self.course_run,
            author=self.scope["user"],
            body=body,
            client_token=client_token,
        )

    def can_send(self) -> bool:
        is_active_user = User.objects.filter(pk=self.scope["user"].pk, is_active=True).exists()
        return is_active_user and can_access_course_chat(self.scope["user"], self.course_run)
