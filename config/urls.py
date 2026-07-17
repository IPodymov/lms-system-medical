from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = []

if settings.ADMIN_URL:
    urlpatterns.append(path(settings.ADMIN_URL, admin.site.urls))

urlpatterns += [
    path("", include("apps.accounts.urls")),
    path("courses/", include("apps.courses.urls")),
    path("learning/", include("apps.learning.urls")),
    path("quizzes/", include("apps.assessments.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("messages/", include("apps.messaging.urls")),
    path("grading/", include("apps.grading.urls")),
    path("api/v1/", include("config.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = "config.views.bad_request"
handler403 = "config.views.permission_denied"
handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"
