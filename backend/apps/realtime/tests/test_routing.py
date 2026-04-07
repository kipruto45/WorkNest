from __future__ import annotations

import uuid

from django.test import SimpleTestCase
from django.urls import resolve

from apps.realtime.routing import websocket_urlpatterns

ROUTING_PATTERNS = tuple(websocket_urlpatterns)


class RealtimeRoutingTests(SimpleTestCase):
    def test_notification_websocket_route_resolves(self) -> None:
        match = resolve("/ws/notifications/", urlconf=ROUTING_PATTERNS)

        self.assertEqual(match.route, "ws/notifications/")

    def test_team_event_websocket_route_resolves(self) -> None:
        team_id = uuid.uuid4()
        match = resolve(f"/ws/teams/{team_id}/events/", urlconf=ROUTING_PATTERNS)

        self.assertEqual(match.route, "ws/teams/<uuid:team_id>/events/")
        self.assertEqual(match.kwargs["team_id"], team_id)
