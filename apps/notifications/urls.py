from django.urls import path

from . import views

urlpatterns = [
    path("", views.list_notifications, name="notifications"),
    path("mark-all-read/", views.mark_all_read, name="mark-all-notifications-read"),
    path("<uuid:notification_id>/", views.notification_detail, name="notification-detail"),
]
