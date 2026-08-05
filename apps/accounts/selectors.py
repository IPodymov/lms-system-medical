from apps.courses.models import CourseRun
from apps.organizations.models import Organization, OrganizationMembership, StudyGroup


def managed_memberships(user):
    if user.is_superuser:
        return OrganizationMembership.objects.select_related("user", "organization")
    organizations = user.memberships.filter(
        role__in=["organization_admin", "teacher"], status="active"
    ).values("organization_id")
    return OrganizationMembership.objects.filter(organization_id__in=organizations).select_related(
        "user", "organization"
    )


def managed_organizations(user):
    if user.is_superuser:
        return Organization.objects.filter(is_active=True)
    organization_ids = user.memberships.filter(
        role__in=["organization_admin", "teacher"], status="active"
    ).values("organization_id")
    return Organization.objects.filter(pk__in=organization_ids, is_active=True)


def can_manage_users(user) -> bool:
    return (
        user.is_superuser
        or user.memberships.filter(role__in=["organization_admin"], status="active").exists()
    )


def can_access_documentation(user) -> bool:
    return (
        user.is_superuser
        or user.memberships.filter(
            role__in=["system_admin", "organization_admin", "teacher"], status="active"
        ).exists()
    )


def can_access_management_documentation(user) -> bool:
    return (
        user.is_superuser
        or user.memberships.filter(
            role__in=["system_admin", "organization_admin"], status="active"
        ).exists()
    )


def managed_course_runs(user):
    return CourseRun.objects.filter(
        course__organization__in=managed_organizations(user)
    ).select_related("course", "course__organization")


def managed_study_groups(user):
    return StudyGroup.objects.filter(
        department__faculty__organization__in=managed_organizations(user)
    ).select_related("department__faculty__organization")


def request_organization(user, organization_id):
    return managed_organizations(user).filter(pk=organization_id).first()
