from django.contrib import admin
from .models import Course, CourseAuthor, CourseRun, CourseRunStaff, CourseSection, Lesson, ContentBlock, TextContent, VideoContent
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display=("title","organization","status","visibility","created_at"); list_filter=("status","visibility","organization"); search_fields=("title","slug"); autocomplete_fields=("organization","created_by")
admin.site.register([CourseAuthor,CourseRun,CourseRunStaff,CourseSection,Lesson,ContentBlock,TextContent,VideoContent])
