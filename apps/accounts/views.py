from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from apps.learning.models import Enrollment


class Login(LoginView):
    template_name = "accounts/login.html"


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    return render(
        request,
        "dashboard.html",
        {
            "enrollments": Enrollment.objects.filter(
                user=request.user, status="active"
            ).select_related("course_run__course")[:6]
        },
    )


@login_required
def profile(request):
    return render(request, "accounts/profile.html")
