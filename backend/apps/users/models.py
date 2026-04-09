from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone as django_timezone

from apps.common.models import TimeStampedUUIDModel
from apps.users.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    class AuthProvider(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"
        GOOGLE = "google", "Google"

    class AccountType(models.TextChoices):
        PERSONAL = "personal", "Personal"
        TEAM = "team", "Team"

    class ThemePreference(models.TextChoices):
        SYSTEM = "system", "System"
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"

    class TwoFactorStatus(models.TextChoices):
        DISABLED = "disabled", "Disabled"
        READY = "ready", "Ready"
        ENABLED = "enabled", "Enabled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    avatar = models.URLField(blank=True, max_length=500)
    bio = models.TextField(blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    notification_preferences = models.JSONField(default=dict, blank=True)
    security_preferences = models.JSONField(default=dict, blank=True)
    auth_provider = models.CharField(
        max_length=20,
        choices=AuthProvider.choices,
        default=AuthProvider.EMAIL,
    )
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.PERSONAL,
    )
    primary_mode = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.PERSONAL,
    )
    onboarding_completed = models.BooleanField(default=False)
    theme_preference = models.CharField(
        max_length=20,
        choices=ThemePreference.choices,
        default=ThemePreference.SYSTEM,
    )
    two_factor_status = models.CharField(
        max_length=20,
        choices=TwoFactorStatus.choices,
        default=TwoFactorStatus.DISABLED,
    )
    email_verified = models.BooleanField(default=False)
    phone_number = models.CharField(max_length=32, unique=True, null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    phone_country_code = models.CharField(max_length=8, blank=True)
    sms_opt_in = models.BooleanField(default=False)
    sms_preferences = models.JSONField(default=dict, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_seen_source = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=django_timezone.now)
    created_at = models.DateTimeField(default=django_timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email_verified", "created_at"]),
            models.Index(fields=["phone_verified", "created_at"]),
            models.Index(fields=["sms_opt_in", "created_at"]),
            models.Index(fields=["theme_preference"]),
            models.Index(fields=["last_seen_at"]),
        ]

    def __str__(self) -> str:
        return self.email or self.phone_number or self.name or str(self.pk)


class PushDevice(TimeStampedUUIDModel):
    class Platform(models.TextChoices):
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"
        WEB = "web", "Web"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="push_devices",
    )
    platform = models.CharField(max_length=20, choices=Platform.choices)
    token = models.CharField(max_length=255)
    label = models.CharField(max_length=120, blank=True)
    app_version = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(default=django_timezone.now)

    class Meta:
        db_table = "push_devices"
        ordering = ["-last_seen_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "token"], name="unique_user_push_token"),
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["platform", "is_active"]),
            models.Index(fields=["last_seen_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} [{self.platform}]"
