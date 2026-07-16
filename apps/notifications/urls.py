from django.urls import path
from . import views
urlpatterns=[path("",views.list_notifications,name="notifications"),path("<uuid:notification_id>/",views.notification_detail,name="notification-detail")]
