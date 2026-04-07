from __future__ import annotations

from django.test import RequestFactory, SimpleTestCase
from rest_framework.permissions import BasePermission

from apps.common.api.mixins import PermissionEnforcerMixin
from apps.common.permissions import IsActiveUser, IsAuthenticatedReadOnly, ReadOnly


class DenyPermission(BasePermission):
    message = "blocked"

    def has_permission(self, request, view):
        return False


class PermissionMixinTests(SimpleTestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_read_only_allows_safe_methods(self) -> None:
        request = self.factory.get("/test/")
        self.assertTrue(ReadOnly().has_permission(request, None))

    def test_is_authenticated_read_only_blocks_unauthenticated_write(self) -> None:
        request = self.factory.post("/test/")
        request.user = type("Anonymous", (), {"is_authenticated": False})()
        self.assertFalse(IsAuthenticatedReadOnly().has_permission(request, None))

    def test_is_active_user_requires_authenticated_active_user(self) -> None:
        request = self.factory.get("/test/")
        request.user = type("User", (), {"is_authenticated": True, "is_active": True})()
        self.assertTrue(IsActiveUser().has_permission(request, None))

    def test_permission_enforcer_raises_permission_denied(self) -> None:
        request = self.factory.get("/test/")
        request.user = type("User", (), {"is_authenticated": True})()
        mixin = PermissionEnforcerMixin()

        with self.assertRaisesMessage(Exception, "blocked"):
            mixin.enforce_permission(request=request, permission_class=DenyPermission)
