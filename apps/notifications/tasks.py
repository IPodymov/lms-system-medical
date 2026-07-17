from celery import shared_task

from .models import Notification


@shared_task
def create_notification(user_id: str, notification_type: str, title: str, body: str) -> None:
    Notification.objects.create(user_id=user_id, type=notification_type, title=title, body=body)
