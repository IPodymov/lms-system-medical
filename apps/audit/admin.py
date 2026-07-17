from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at", "old_data", "new_data")
    list_display = ("action", "entity_type", "actor", "created_at")
    search_fields = ("action", "entity_type")
