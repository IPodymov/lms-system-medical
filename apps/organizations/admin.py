from django.contrib import admin

from .models import (
    Department,
    Faculty,
    Organization,
    OrganizationMembership,
    StudyGroup,
    StudyGroupMember,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    search_fields = ("name", "short_name", "slug")
    list_display = ("short_name", "name", "is_active")


admin.site.register([OrganizationMembership, Faculty, Department, StudyGroup, StudyGroupMember])
