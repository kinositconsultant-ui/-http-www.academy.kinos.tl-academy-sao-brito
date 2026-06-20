from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class Role(models.TextChoices):
    ADMIN = "admin", _("Administrator")
    PRINCIPAL = "principal", _("Principal")
    TEACHER = "teacher", _("Teacher")
    ACCOUNTANT = "accountant", _("Accountant")
    HR = "hr", _("HR Manager")
    STAFF = "staff", _("Staff")
    PARENT = "parent", _("Parent")
    STUDENT = "student", _("Student")


class User(AbstractUser):
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.STAFF
    )
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def display_name(self):
        return self.get_full_name() or self.username


class School(models.Model):
    """Single-tenant school profile (singleton). First row is the active school."""

    name = models.CharField(max_length=200)
    registration_no = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    founded_date = models.DateField(blank=True, null=True)
    motto = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to="school/", blank=True, null=True)
    currency = models.CharField(max_length=8, default="USD")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "School"
        verbose_name_plural = "School"

    def __str__(self):
        return self.name

    @classmethod
    def get_active(cls):
        return cls.objects.order_by("id").first()
