from __future__ import annotations

from django.conf import settings
from rest_framework import permissions


def is_configured_platform_admin(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False) or not getattr(user, "is_active", False):
        return False
    configured_admin_email = str(getattr(settings, "ADMIN_EMAIL", "")).strip().lower()
    if configured_admin_email:
        return bool(getattr(user, "is_staff", False) and str(getattr(user, "email", "")).strip().lower() == configured_admin_email)
    return bool(getattr(user, "is_staff", False))


class IsConfiguredPlatformAdmin(permissions.BasePermission):
    message = "You do not have permission to access platform administration."

    def has_permission(self, request, view):
        return is_configured_platform_admin(getattr(request, "user", None))
