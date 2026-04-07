from __future__ import annotations

from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


def build_anonymous_user():
    from django.contrib.auth.models import AnonymousUser

    return AnonymousUser()


@database_sync_to_async
def get_user_for_token(raw_token: str):
    authenticator = JWTAuthentication()
    validated_token = authenticator.get_validated_token(raw_token)
    return authenticator.get_user(validated_token)


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        mutable_scope = dict(scope)
        current_user = mutable_scope.get("user")
        if not getattr(current_user, "is_authenticated", False):
            query_string = mutable_scope.get("query_string", b"").decode("utf-8")
            token = parse_qs(query_string).get("token", [None])[0]
            if token:
                try:
                    mutable_scope["user"] = await get_user_for_token(token)
                except (InvalidToken, TokenError, Exception):
                    mutable_scope["user"] = build_anonymous_user()

        return await self.inner(mutable_scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(AuthMiddlewareStack(inner))
