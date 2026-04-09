from __future__ import annotations

from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class LenientJWTAuthentication(JWTAuthentication):
    """
    Public auth entrypoints should ignore stale bearer tokens instead of failing
    before the view can handle the request.
    """

    def authenticate(self, request):  # type: ignore[override]
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except (InvalidToken, TokenError, exceptions.AuthenticationFailed):
            return None
