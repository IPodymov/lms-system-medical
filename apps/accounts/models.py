import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: abstract = True

class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class Meta: abstract = True

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email: raise ValueError("Email обязателен")
        user = self.model(email=self.normalize_email(email), username=email, **extra_fields)
        user.set_password(password); user.save(using=self._db); return user
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.update(is_staff=True, is_superuser=True)
        return self.create_user(email, password, **extra_fields)

class User(UUIDModel, TimeStampedModel, AbstractUser):
    username = models.CharField(max_length=254, unique=True, blank=True)
    email = models.EmailField(unique=True)
    middle_name = models.CharField(max_length=150, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()
    def __str__(self): return self.get_full_name() or self.email
