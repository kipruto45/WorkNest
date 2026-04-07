from rest_framework.permissions import AllowAny, IsAuthenticated


class AuthEntryPointPermission(AllowAny):
    """Explicit permission for public auth entry points."""


class AuthenticatedSessionPermission(IsAuthenticated):
    """Explicit permission for authenticated session-bound auth actions."""
