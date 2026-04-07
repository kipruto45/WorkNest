"""Central WebSocket route registry."""

from apps.realtime.routing import websocket_urlpatterns as realtime_websocket_urlpatterns

websocket_urlpatterns = [
    *realtime_websocket_urlpatterns,
]
