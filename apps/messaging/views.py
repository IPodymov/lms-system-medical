from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.courses.models import CourseRun
from apps.notifications.models import Notification

from .forms import CourseMessageForm, DirectMessageForm
from .models import CourseMessage, DirectMessage

User = get_user_model()


@login_required
def direct_messages(request, user_id=None):
    recipient = None
    if user_id:
        recipient = get_object_or_404(User, pk=user_id, is_active=True)
        if recipient == request.user:
            messages.info(request, "Выберите другого пользователя для переписки.")
            return redirect("direct-messages")

    if request.method == "POST":
        if not recipient:
            return HttpResponseForbidden()
        form = DirectMessageForm(request.POST, request.FILES)
        if form.is_valid():
            item, created = DirectMessage.objects.get_or_create(
                client_token=form.cleaned_data["client_token"],
                defaults={
                    "sender": request.user,
                    "recipient": recipient,
                    "body": form.cleaned_data["body"],
                    "attachment": form.cleaned_data.get("attachment"),
                    "attachment_content_type": getattr(
                        form.cleaned_data.get("attachment"), "content_type", ""
                    ),
                },
            )
            if created:
                Notification.objects.create(
                    user=recipient,
                    type="direct_message",
                    title="Новое личное сообщение",
                    body=f"{request.user.get_full_name() or request.user.email}: {item.body[:120]}",
                    payload={"sender_id": str(request.user.pk)},
                )
            return redirect("direct-message-thread", user_id=recipient.pk)
    else:
        form = DirectMessageForm()

    thread = DirectMessage.objects.none()
    if recipient:
        thread = DirectMessage.objects.filter(
            Q(sender=request.user, recipient=recipient)
            | Q(sender=recipient, recipient=request.user)
        ).select_related("sender", "recipient")
        thread.filter(recipient=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )

    query = request.GET.get("q", "").strip()
    contacts = (
        User.objects.filter(is_active=True)
        .exclude(pk=request.user.pk)
        .order_by("first_name", "last_name", "email")
    )
    if query:
        contacts = contacts.filter(Q(username__icontains=query) | Q(email__icontains=query))
    contacts = contacts[:50]
    return render(
        request,
        "messaging/direct_messages.html",
        {
            "contacts": contacts,
            "recipient": recipient,
            "thread": thread,
            "form": form,
            "query": query,
        },
    )


def _can_access_course_chat(user, course_run):
    return (
        user.is_superuser
        or course_run.enrollments.filter(user=user).exists()
        or course_run.staff.filter(user=user).exists()
    )


@login_required
def course_chat(request, run_id):
    course_run = get_object_or_404(CourseRun.objects.select_related("course"), pk=run_id)
    if not _can_access_course_chat(request.user, course_run):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = CourseMessageForm(request.POST, request.FILES)
        if form.is_valid():
            item, created = CourseMessage.objects.get_or_create(
                client_token=form.cleaned_data["client_token"],
                defaults={
                    "course_run": course_run,
                    "author": request.user,
                    "body": form.cleaned_data["body"],
                    "attachment": form.cleaned_data.get("attachment"),
                    "attachment_content_type": getattr(
                        form.cleaned_data.get("attachment"), "content_type", ""
                    ),
                },
            )
            if created:
                recipients = course_run.enrollments.exclude(user=request.user).values_list(
                    "user_id", flat=True
                )
                Notification.objects.bulk_create(
                    [
                        Notification(
                            user_id=user_id,
                            type="course_chat",
                            title=f"Новое сообщение в чате: {course_run.title}",
                            body=(
                                f"{request.user.get_full_name() or request.user.email}: "
                                f"{item.body[:120]}"
                            ),
                            payload={"course_run_id": str(course_run.pk)},
                        )
                        for user_id in recipients
                    ]
                )
            return redirect("course-chat", run_id=course_run.pk)
    else:
        form = CourseMessageForm()
    return render(
        request,
        "messaging/course_chat.html",
        {
            "course_run": course_run,
            "chat_messages": CourseMessage.objects.filter(course_run=course_run).select_related(
                "author"
            ),
            "form": form,
        },
    )
