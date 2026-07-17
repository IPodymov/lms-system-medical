from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Notification


@login_required
def list_notifications(request):
    return render(
        request, "notifications/list.html", {"notifications": request.user.notifications.all()}
    )


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
