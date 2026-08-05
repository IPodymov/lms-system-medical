import secrets
from datetime import date

from django.db import transaction
from django.utils.text import slugify

from apps.organizations.models import (
    Department,
    Faculty,
    Organization,
    OrganizationMembership,
    StudyGroup,
    StudyGroupMember,
)

from .models import User


def organization_slug(name: str) -> str:
    max_length = Organization._meta.get_field("slug").max_length or 50
    base_slug = (slugify(name) or "organization")[:max_length]
    slug, index = base_slug, 2
    while Organization.objects.filter(slug=slug).exists():
        suffix = f"-{index}"
        slug = f"{base_slug[: max_length - len(suffix)]}{suffix}"
        index += 1
    return slug


def default_department(organization):
    faculty, _ = Faculty.objects.get_or_create(
        organization=organization,
        code="general",
        defaults={"name": "Общее отделение"},
    )
    return Department.objects.get_or_create(
        faculty=faculty,
        code="general",
        defaults={"name": "Общее направление"},
    )[0]


def set_user_identity(user, *, first_name, last_name, middle_name):
    user.first_name = first_name
    user.last_name = last_name
    user.middle_name = middle_name
    user.save(update_fields=["first_name", "last_name", "middle_name"])


def get_or_create_user(*, email, password, first_name, last_name, middle_name, username=None):
    user, created = User.objects.get_or_create(
        email=email, defaults={"username": username or email}
    )
    if created:
        user.set_password(password)
    set_user_identity(user, first_name=first_name, last_name=last_name, middle_name=middle_name)
    if created:
        user.save(update_fields=["password"])
    return user, created


def generated_login() -> str:
    while True:
        login_name = f"student-{secrets.token_hex(4)}"
        if not User.objects.filter(username=login_name).exists():
            return login_name


def generated_password() -> str:
    return secrets.token_urlsafe(12)


def split_full_name(full_name: str) -> tuple[str, str, str]:
    parts = full_name.split()
    if len(parts) < 2:
        raise ValueError("Укажите ФИО: фамилию и имя.")
    return parts[1], parts[0], " ".join(parts[2:])


def add_student_to_group(*, user, organization, study_group, student_number=""):
    membership, created = OrganizationMembership.objects.get_or_create(
        user=user,
        organization=organization,
        defaults={
            "role": OrganizationMembership.Role.STUDENT,
            "status": "active",
            "student_number": student_number,
        },
    )
    if not created and membership.role == OrganizationMembership.Role.STUDENT:
        membership.student_number = student_number or membership.student_number
        membership.status = "active"
        membership.save(update_fields=["student_number", "status", "updated_at"])
    StudyGroupMember.objects.update_or_create(
        study_group=study_group, user=user, defaults={"left_at": None}
    )


def excel_column_map(headers):
    aliases = {
        "email": {"email", "e-mail", "почта", "электронная почта"},
        "username": {"username", "login", "логин", "имя пользователя"},
        "password": {"password", "пароль", "временный пароль"},
        "full_name": {"full_name", "full name", "фио", "фамилия имя отчество"},
        "first_name": {"first_name", "имя"},
        "last_name": {"last_name", "фамилия"},
        "middle_name": {"middle_name", "отчество"},
        "student_number": {"student_number", "номер студента", "зачетная книжка"},
        "group": {"group", "группа"},
        "admission_year": {"admission_year", "год поступления"},
        "graduation_year": {"graduation_year", "год выпуска"},
    }
    normalized = {
        str(value).strip().lower(): index
        for index, value in enumerate(headers)
        if value is not None
    }
    return {
        field: next((normalized[name] for name in names if name in normalized), None)
        for field, names in aliases.items()
    }


def bootstrap_superuser_membership(user, managed_organizations) -> bool:
    """Give a console-created superuser a manageable membership and adopt orphan users.

    Console-created superusers have no `OrganizationMembership`. On their first visit to the
    admin dashboard, make them (and any other membership-less user) visible and manageable in
    the first active organization, without affecting existing roles. Returns whether a default
    organization was available to bootstrap into.
    """
    default_organization = managed_organizations.order_by("created_at").first()
    if not default_organization:
        return False
    for candidate in User.objects.filter(memberships__isnull=True):
        OrganizationMembership.objects.get_or_create(
            user=candidate,
            organization=default_organization,
            defaults={"role": OrganizationMembership.Role.STUDENT},
        )
    OrganizationMembership.objects.update_or_create(
        user=user,
        organization=default_organization,
        defaults={"role": OrganizationMembership.Role.SYSTEM_ADMIN, "status": "active"},
    )
    return True


def parse_student_import_rows(workbook) -> list[tuple[int, dict, int, int]]:
    """Parse an uploaded student-roster workbook into validated rows.

    Raises ValueError (with a user-facing message) on any structural or per-row problem.
    """
    rows = workbook.active.iter_rows(values_only=True)
    headers = next(rows, None)
    columns = excel_column_map(headers or [])
    has_name_columns = columns["full_name"] is not None or (
        columns["first_name"] is not None and columns["last_name"] is not None
    )
    if not headers or columns["group"] is None or not has_name_columns:
        raise ValueError(
            "Excel должен содержать колонки group и full_name (или first_name, last_name)."
        )
    parsed_rows = []
    for row_number, row in enumerate(rows, start=2):
        if not any(value not in (None, "") for value in row):
            continue
        values = {
            field: str(row[index]).strip() if index is not None and row[index] is not None else ""
            for field, index in columns.items()
        }
        if not values["group"]:
            raise ValueError(f"Строка {row_number}: укажите номер группы.")
        if values["full_name"]:
            values["first_name"], values["last_name"], values["middle_name"] = split_full_name(
                values["full_name"]
            )
        if not values["first_name"] or not values["last_name"]:
            raise ValueError(f"Строка {row_number}: укажите ФИО студента.")
        try:
            admission_year = int(values["admission_year"] or date.today().year)
            graduation_year = int(values["graduation_year"] or admission_year + 4)
        except ValueError as error:
            raise ValueError(f"Строка {row_number}: укажите годы числами.") from error
        if graduation_year <= admission_year:
            raise ValueError(
                f"Строка {row_number}: год выпуска должен быть больше года поступления."
            )
        parsed_rows.append((row_number, values, admission_year, graduation_year))
    return parsed_rows


@transaction.atomic
def import_students(*, organization, parsed_rows):
    """Create/update students and study groups from parsed import rows.

    Returns (created_students_count, generated_credentials) where generated_credentials is a
    list of (last_name, first_name, group, username, email, password) tuples for rows where a
    login or password had to be auto-generated.
    """
    department = default_department(organization)
    created_students = 0
    generated_credentials = []
    for _, values, admission_year, graduation_year in parsed_rows:
        group, _ = StudyGroup.objects.get_or_create(
            department=department,
            name=values["group"],
            admission_year=admission_year,
            defaults={"graduation_year": graduation_year},
        )
        username = values["username"] or generated_login()
        email = values["email"].lower() or f"{username}@import.local"
        password = values["password"] or generated_password()
        user, created = get_or_create_user(
            email=email,
            password=password,
            first_name=values["first_name"],
            last_name=values["last_name"],
            middle_name=values["middle_name"],
            username=username,
        )
        add_student_to_group(
            user=user,
            organization=organization,
            study_group=group,
            student_number=values["student_number"],
        )
        created_students += int(created)
        if created and (not values["email"] or not values["password"]):
            generated_credentials.append(
                (
                    values["last_name"],
                    values["first_name"],
                    values["group"],
                    user.username,
                    user.email,
                    password,
                )
            )
    return created_students, generated_credentials
