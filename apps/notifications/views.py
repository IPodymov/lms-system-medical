from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Notification

NOTIFICATIONS_PER_PAGE = 20


@login_required
def list_notifications(request):
    # Сортировка обязательна: без неё Paginator режет неупорядоченную выборку
    # и одно и то же уведомление может попасть на две страницы сразу.
    # Порядок совпадает с индексом (user, is_read, created_at).
    notifications = Paginator(
        request.user.notifications.order_by("-created_at"), NOTIFICATIONS_PER_PAGE
    ).get_page(request.GET.get("page"))
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
def notification_detail(request, notification_id):
    item = get_object_or_404(Notification, user=request.user, pk=notification_id)
    item.is_read = True
    item.read_at = timezone.now()
    item.save(update_fields=["is_read", "read_at"])
    return render(request, "notifications/detail.html", {"item": item})


@login_required
def mark_all_read(request):
    if request.method == "POST":
        request.user.notifications.filter(is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
    return redirect("notifications")
