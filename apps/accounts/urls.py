from django.urls import path
from . import views
urlpatterns=[path("",views.dashboard,name="dashboard"),path("login/",views.Login.as_view(),name="login"),path("logout/",views.logout_view,name="logout"),path("profile/",views.profile,name="profile")]
