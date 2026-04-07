from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsNotificationOwner(BasePermission):
    message = "You do not have permission to access this notification."

    def has_object_permission(self, request, view, obj) -> bool:
        return obj.user_id == request.user.id
