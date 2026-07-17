from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    fieldsets = UserAdmin.fieldsets + (("Дополнительно", {"fields": ("middle_name", "avatar")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Дополнительно", {"fields": ("email", "first_name", "last_name", "middle_name")}),
    )
