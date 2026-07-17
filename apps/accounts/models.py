import uuid
from typing import Any

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class UserManager(BaseUserManager["User"]):
    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> "User":
        if not email:
            raise ValueError("Email обязателен")
        user = self.model(email=self.normalize_email(email), username=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> "User":
        extra_fields.update(is_staff=True, is_superuser=True)
        return self.create_user(email, password, **extra_fields)


class User(UUIDModel, TimeStampedModel, AbstractUser):
    username = models.CharField(max_length=254, unique=True, blank=True)
    email = models.EmailField(unique=True)
    middle_name = models.CharField(max_length=150, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects: UserManager = UserManager()  # type: ignore[misc, assignment]

    def get_full_name(self) -> str:
        """Return the full Russian-style name used across the interface."""
        return " ".join(
            part
            for part in (
                self.last_name.strip(),
                self.first_name.strip(),
                self.middle_name.strip(),
            )
            if part
        )

    def __str__(self) -> str:
        return self.get_full_name() or self.email
