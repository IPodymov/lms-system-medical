from django.contrib import admin
from .models import Enrollment,ContentProgress
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin): list_display=("user","course_run","status","progress_percent"); list_filter=("status",); search_fields=("user__email","course_run__title"); autocomplete_fields=("user",)
admin.site.register(ContentProgress)
