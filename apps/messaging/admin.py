from django.contrib import admin

from .models import CourseMessage, DirectMessage


@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "recipient", "created_at", "is_read")
    search_fields = ("sender__email", "recipient__email", "body")
    list_filter = ("is_read",)


@admin.register(CourseMessage)
class CourseMessageAdmin(admin.ModelAdmin):
    list_display = ("course_run", "author", "created_at")
    search_fields = ("author__email", "body", "course_run__title")
