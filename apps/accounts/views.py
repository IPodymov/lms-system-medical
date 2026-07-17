from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from apps.courses.models import CourseRunStaff
from apps.learning.models import Enrollment
from apps.organizations.models import Organization, OrganizationMembership

from .forms import ProfileForm, RegistrationForm, UserPasswordForm
from .models import User


class Login(LoginView):
    template_name = "accounts/login.html"


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Аккаунт создан. Добро пожаловать в МедЛМС.")
        return redirect("dashboard")
    return render(request, "accounts/register.html", {"form": form})


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
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "profile":
            profile_form = ProfileForm(request.POST, request.FILES, instance=request.user)
            password_form = UserPasswordForm(request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Профиль сохранён.")
                return redirect("profile")
        elif action == "password":
            profile_form = ProfileForm(instance=request.user)
            password_form = UserPasswordForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Пароль изменён.")
                return redirect("profile")
        else:
            profile_form = ProfileForm(instance=request.user)
            password_form = UserPasswordForm(request.user)
    else:
        profile_form = ProfileForm(instance=request.user)
        password_form = UserPasswordForm(request.user)
    history = request.user.enrollments.select_related("course_run__course").order_by("-updated_at")
    return render(
        request,
        "accounts/profile.html",
        {
            "profile_form": profile_form,
            "password_form": password_form,
            "history": history,
        },
    )


def _managed_memberships(user):
    if user.is_superuser:
        return OrganizationMembership.objects.select_related("user", "organization")
    organizations = user.memberships.filter(
        role__in=["organization_admin", "teacher"], status="active"
    ).values("organization_id")
    return OrganizationMembership.objects.filter(organization_id__in=organizations).select_related(
        "user", "organization"
    )


def _managed_organizations(user):
    if user.is_superuser:
        return Organization.objects.filter(is_active=True)
    organization_ids = user.memberships.filter(
        role__in=["organization_admin", "teacher"], status="active"
    ).values("organization_id")
    return Organization.objects.filter(pk__in=organization_ids, is_active=True)


def _can_manage_users(user) -> bool:
    return (
        user.is_superuser
        or user.memberships.filter(role__in=["organization_admin"], status="active").exists()
    )


def _organization_slug(name: str) -> str:
    max_length = Organization._meta.get_field("slug").max_length or 50
    base_slug = (slugify(name) or "organization")[:max_length]
    slug, index = base_slug, 2
    while Organization.objects.filter(slug=slug).exists():
        suffix = f"-{index}"
        slug = f"{base_slug[: max_length - len(suffix)]}{suffix}"
        index += 1
    return slug


@login_required
def admin_dashboard(request):
    memberships = _managed_memberships(request.user)
    managed_organizations = _managed_organizations(request.user)
    if not managed_organizations.exists():
        if not request.user.is_superuser:
            raise PermissionDenied
        return render(
            request,
            "accounts/admin_dashboard.html",
            {
                "memberships": memberships,
                "progress": [],
                "metrics": {"users": 0, "students": 0, "average_progress": 0, "completed": 0},
                "can_manage_users": False,
                "can_create_organizations": True,
                "institution_types": Organization.InstitutionType.choices,
                "roles": OrganizationMembership.Role.choices,
                "organizations": [],
            },
        )
    if request.user.is_superuser:
        # Console-created users have no membership. Make them visible and manageable in the
        # first active organization, without affecting existing roles.
        default_organization = managed_organizations.order_by("created_at").first()
        if default_organization:
            for user in User.objects.filter(memberships__isnull=True):
                OrganizationMembership.objects.get_or_create(
                    user=user,
                    organization=default_organization,
                    defaults={"role": OrganizationMembership.Role.STUDENT},
                )
            OrganizationMembership.objects.update_or_create(
                user=request.user,
                organization=default_organization,
                defaults={"role": OrganizationMembership.Role.SYSTEM_ADMIN, "status": "active"},
            )
            memberships = _managed_memberships(request.user)
    enrollments = Enrollment.objects.filter(
        course_run__course__organization__in=managed_organizations
    )
    if not request.user.is_superuser:
        run_ids = CourseRunStaff.objects.filter(
            user=request.user, role__in=["teacher", "assistant"]
        ).values("course_run_id")
        enrollments = enrollments.filter(course_run_id__in=run_ids)
    progress = enrollments.select_related("user", "course_run__course").order_by(
        "progress_percent", "-updated_at"
    )[:30]
    return render(
        request,
        "accounts/admin_dashboard.html",
        {
            "memberships": memberships.order_by("user__email")[:50],
            "progress": progress,
            "metrics": {
                "users": memberships.values("user_id").distinct().count(),
                "students": enrollments.values("user_id").distinct().count(),
                "average_progress": enrollments.aggregate(value=Avg("progress_percent"))["value"]
                or 0,
                "completed": enrollments.filter(status="completed").count(),
            },
            "can_manage_users": _can_manage_users(request.user),
            "can_create_organizations": request.user.is_superuser,
            "institution_types": Organization.InstitutionType.choices,
            "roles": OrganizationMembership.Role.choices,
            "organizations": managed_organizations,
        },
    )


@login_required
def add_organization(request):
    if request.method != "POST" or not request.user.is_superuser:
        raise PermissionDenied

    name = request.POST.get("name", "").strip()
    short_name = request.POST.get("short_name", "").strip()
    institution_type = request.POST.get("institution_type", "")
    if not name or not short_name or institution_type not in Organization.InstitutionType.values:
        messages.error(request, "Укажите название, сокращение и тип организации.")
        return redirect("admin-dashboard")

    organization = Organization.objects.create(
        name=name,
        short_name=short_name,
        slug=_organization_slug(name),
        institution_type=institution_type,
    )
    OrganizationMembership.objects.update_or_create(
        user=request.user,
        organization=organization,
        defaults={"role": OrganizationMembership.Role.SYSTEM_ADMIN, "status": "active"},
    )
    messages.success(request, "Организация создана. Теперь можно создавать и редактировать курсы.")
    return redirect("admin-dashboard")


@login_required
def manage_user_role(request, membership_id):
    if request.method != "POST" or not _can_manage_users(request.user):
        raise PermissionDenied
    membership = get_object_or_404(_managed_memberships(request.user), pk=membership_id)
    role = request.POST.get("role")
    if role in OrganizationMembership.Role.values:
        membership.role = role
        membership.save(update_fields=["role", "updated_at"])
        messages.success(request, "Роль пользователя обновлена.")
    return redirect("admin-dashboard")


@login_required
def add_user(request):
    if request.method != "POST" or not _can_manage_users(request.user):
        raise PermissionDenied
    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")
    role = request.POST.get("role", OrganizationMembership.Role.STUDENT)
    organization_id = request.POST.get("organization_id")
    organization = (
        _managed_memberships(request.user)
        .filter(organization_id=organization_id)
        .values_list("organization", flat=True)
        .first()
    )
    if not email or not password or not organization:
        messages.error(request, "Укажите email, временный пароль и организацию.")
        return redirect("admin-dashboard")
    try:
        validate_password(password)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
        return redirect("admin-dashboard")
    user, created = User.objects.get_or_create(email=email, defaults={"username": email})
    if created:
        user.set_password(password)
        user.save(update_fields=["password"])
    OrganizationMembership.objects.update_or_create(
        user=user, organization_id=organization, defaults={"role": role, "status": "active"}
    )
    messages.success(
        request,
        "Пользователь добавлен. Передайте ему заданный временный пароль безопасным способом.",
    )
    return redirect("admin-dashboard")
