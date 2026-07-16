from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls), path("", include("apps.accounts.urls")),
    path("courses/", include("apps.courses.urls")), path("learning/", include("apps.learning.urls")),
    path("notifications/", include("apps.notifications.urls")), path("grading/", include("apps.grading.urls")),
    path("api/v1/", include("config.api_urls")), path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
