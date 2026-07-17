from django.conf import settings
from django.db import models

from apps.accounts.models import TimeStampedModel, UUIDModel


class Organization(UUIDModel, TimeStampedModel):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    settings = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.short_name


class OrganizationMembership(TimeStampedModel):
    class Role(models.TextChoices):
        SYSTEM_ADMIN = "system_admin", "Системный администратор"
        ORGANIZATION_ADMIN = "organization_admin", "Администратор"
        TEACHER = "teacher", "Преподаватель"
        ASSISTANT = "assistant", "Ассистент"
        STUDENT = "student", "Студент"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=24, choices=Role)
    status = models.CharField(max_length=16, default="active")
    student_number = models.CharField(max_length=64, blank=True)
    employee_number = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "user"], name="unique_org_member")
        ]


class Faculty(TimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=32)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="unique_faculty_code")
        ]


class Department(TimeStampedModel):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=32)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["faculty", "code"], name="unique_department_code")
        ]


class StudyGroup(TimeStampedModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    admission_year = models.PositiveIntegerField()
    graduation_year = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["department", "name", "admission_year"], name="unique_study_group"
            )
        ]


class StudyGroupMember(models.Model):
    study_group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joined_at = models.DateField(auto_now_add=True)
    left_at = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["study_group", "user"], name="unique_group_member")
        ]
