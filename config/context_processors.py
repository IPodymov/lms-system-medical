from pathlib import Path

from django.conf import settings
from django.http import HttpRequest

from apps.messaging.models import DirectMessage


def navigation_context(request: HttpRequest) -> dict[str, int]:
    """Expose compact navigation counters without querying for anonymous visitors."""
    if not request.user.is_authenticated:
        return {
            "unread_notifications_count": 0,
            "unread_messages_count": 0,
            "can_open_management": False,
            "can_create_course": False,
            "can_access_documentation": False,
        }

    return {
        "unread_notifications_count": request.user.notifications.filter(
            is_read=False
        ).count(),
        "unread_messages_count": DirectMessage.objects.filter(
            recipient=request.user, is_read=False
        ).count(),
        "can_open_management": request.user.is_superuser
        or request.user.memberships.filter(
            role__in=["organization_admin", "teacher"], status="active"
        ).exists(),
        "can_create_course": request.user.is_superuser
        or request.user.memberships.filter(
            role__in=["teacher", "assistant", "organization_admin", "system_admin"],
            status="active",
        ).exists(),
        "can_access_documentation": request.user.is_superuser
        or request.user.memberships.filter(
            role__in=["teacher", "organization_admin", "system_admin"], status="active"
        ).exists(),
    }


def static_asset_version(_: HttpRequest) -> dict[str, str]:
    """Cache-bust local CSS while production keeps manifest-hashed asset names."""
    css_root = Path(settings.BASE_DIR) / "static" / "css"
    version = max(
        (item.stat().st_mtime_ns for item in css_root.rglob("*.css")), default=0
    )
    return {"static_asset_version": str(version)}
