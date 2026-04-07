"""ASGI entrypoint for HTTP and WebSocket traffic."""

from __future__ import annotations

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from apps.realtime.middleware import JWTAuthMiddlewareStack
from config.websocket import websocket_urlpatterns


def _default_settings_module() -> str:
    if os.environ.get("ENVIRONMENT", "").strip().lower() == "production":
        return "config.settings.production"
    return "config.settings.local"


os.environ.setdefault("DJANGO_SETTINGS_MODULE", _default_settings_module())

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
