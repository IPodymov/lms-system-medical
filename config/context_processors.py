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
        "unread_notifications_count": request.user.notifications.filter(is_read=False).count(),
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
    """Cache-bust static assets during development only.

    In production WhiteNoise already puts a content hash into every file name,
    so an extra query string adds nothing — while the directory scan it needs
    would run on every single request. Development has no manifest, so without
    the suffix the browser keeps serving a stale stylesheet after each edit.

    The returned value is the full suffix (including "?"), so templates can
    append it unconditionally and get nothing at all in production.
    """
    if not settings.DEBUG:
        return {"static_asset_version": ""}

    css_root = Path(settings.BASE_DIR) / "static"
    version = max(
        (item.stat().st_mtime_ns for item in css_root.rglob("*.css")),
        default=0,
    )
    return {"static_asset_version": f"?v={version}"}
