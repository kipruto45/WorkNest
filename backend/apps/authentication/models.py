from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TimestampedModel


class LoginActivity(TimestampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="login_activities",
        null=True,
        blank=True,
    )
    email = models.EmailField()
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
