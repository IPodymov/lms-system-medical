from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.Login.as_view(), name="login"),
    path("register/", views.register, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("management/", views.admin_dashboard, name="admin-dashboard"),
    path("management/users/add/", views.add_user, name="add-user"),
    path(
        "management/users/<int:membership_id>/role/",
        views.manage_user_role,
        name="manage-user-role",
    ),
]
