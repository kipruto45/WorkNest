from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimestampedModel
from apps.common.models import TimeStampedUUIDModel


class LoginActivity(TimestampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="login_activities",
        null=True,
        blank=True,
    )
    email = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "login_activities"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "created_at"]),
            models.Index(fields=["success", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} - {'success' if self.success else 'failure'}"


class EmailVerificationToken(TimeStampedUUIDModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "email_verification_tokens"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "expires_at"]),
            models.Index(fields=["used_at", "expires_at"]),
        ]

    @property
    def is_active(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()


class AuthSession(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auth_sessions",
    )
    session_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    refresh_token_jti = models.CharField(max_length=255, unique=True)
    device_name = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        db_table = "auth_sessions"
        ordering = ["-last_seen_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["refresh_token_jti"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.session_key}"


class PhoneVerificationCode(TimeStampedUUIDModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="phone_verification_codes",
    )
    phone_number = models.CharField(max_length=32)
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "phone_verification_codes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "expires_at"]),
            models.Index(fields=["phone_number", "expires_at"]),
            models.Index(fields=["used_at", "expires_at"]),
        ]

    @property
    def is_active(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()
