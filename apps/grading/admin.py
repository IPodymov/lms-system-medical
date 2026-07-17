from django.contrib import admin

from .models import Grade, GradebookItem

admin.site.register([GradebookItem, Grade])
