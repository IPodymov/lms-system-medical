from django.urls import path

from . import views

urlpatterns = [path("runs/<uuid:run_id>/", views.gradebook, name="gradebook")]
