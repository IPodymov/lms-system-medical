from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.courses.models import CourseRun
from apps.organizations.models import OrganizationMembership

from .forms import CourseMessageForm, DirectMessageForm
from .models import CourseMessage, DirectMessage, FavoriteContact
from .permissions import can_access_course_chat
from .services import create_course_message, create_direct_message

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
            create_direct_message(
                sender=request.user,
                recipient=recipient,
                body=form.cleaned_data["body"],
                attachment=form.cleaned_data.get("attachment"),
                client_token=form.cleaned_data["client_token"],
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
    favorite_contact = FavoriteContact.objects.filter(user=request.user, contact_id=OuterRef("pk"))
    sent_contact_ids = DirectMessage.objects.filter(sender=request.user).values("recipient_id")
    received_contact_ids = DirectMessage.objects.filter(recipient=request.user).values("sender_id")
    recent_contacts = (
        User.objects.filter(is_active=True)
        .exclude(pk=request.user.pk)
        .filter(
            Q(pk__in=sent_contact_ids)
            | Q(pk__in=received_contact_ids)
            | Q(favorited_by__user=request.user)
        )
        .annotate(is_favorite=Exists(favorite_contact))
        .distinct()
        .order_by("-is_favorite", "first_name", "last_name", "email")
    )
    if query:
        name_query = Q()
        for part in query.split():
            name_query &= (
                Q(username__icontains=part)
                | Q(email__icontains=part)
                | Q(first_name__icontains=part)
                | Q(last_name__icontains=part)
                | Q(middle_name__icontains=part)
            )
        contacts = (
            User.objects.filter(is_active=True)
            .exclude(pk=request.user.pk)
            .filter(name_query)
            .annotate(is_favorite=Exists(favorite_contact))
            .order_by("-is_favorite", "last_name", "first_name", "middle_name", "email")
        )
    else:
        contacts = recent_contacts
    contacts = contacts[:50]
    recipient_membership = None
    if recipient:
        recipient_membership = (
            OrganizationMembership.objects.filter(user=recipient, status="active")
            .select_related("organization")
            .order_by("organization__short_name")
            .first()
        )
    return render(
        request,
        "messaging/direct_messages.html",
        {
            "contacts": contacts,
            "recipient": recipient,
            "thread": thread,
            "form": form,
            "query": query,
            "recipient_is_favorite": bool(
                recipient
                and FavoriteContact.objects.filter(user=request.user, contact=recipient).exists()
            ),
            "recipient_membership": recipient_membership,
        },
    )


@login_required
def toggle_favorite_contact(request, user_id):
    if request.method != "POST":
        return HttpResponseForbidden()
    contact = get_object_or_404(User, pk=user_id, is_active=True)
    if contact == request.user:
        return HttpResponseForbidden()
    favorite, created = FavoriteContact.objects.get_or_create(user=request.user, contact=contact)
    if created:
        messages.success(request, "Пользователь добавлен в избранное.")
    else:
        favorite.delete()
        messages.success(request, "Пользователь убран из избранного.")
    return redirect("direct-message-thread", user_id=contact.pk)


@login_required
def course_chat(request, run_id):
    course_run = get_object_or_404(CourseRun.objects.select_related("course"), pk=run_id)
    if not can_access_course_chat(request.user, course_run):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = CourseMessageForm(request.POST, request.FILES)
        if form.is_valid():
            create_course_message(
                course_run=course_run,
                author=request.user,
                body=form.cleaned_data["body"],
                attachment=form.cleaned_data.get("attachment"),
                client_token=form.cleaned_data["client_token"],
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
