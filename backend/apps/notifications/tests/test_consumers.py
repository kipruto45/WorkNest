from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from apps.notifications.consumers import NotificationConsumer


class NotificationConsumerTests(unittest.IsolatedAsyncioTestCase):
    async def test_connect_adds_authenticated_user_to_group(self) -> None:
        consumer = NotificationConsumer()
        consumer.scope = {
            "type": "websocket",
            "user": SimpleNamespace(is_authenticated=True, id="user-123"),
        }
        consumer.channel_layer = AsyncMock()
        consumer.channel_name = "test-channel"
        consumer.accept = AsyncMock()

        await consumer.connect()

        consumer.channel_layer.group_add.assert_awaited_once_with("user_user-123", "test-channel")
        consumer.accept.assert_awaited_once()

    async def test_connect_rejects_unauthenticated_user(self) -> None:
        consumer = NotificationConsumer()
        consumer.scope = {
            "type": "websocket",
            "user": SimpleNamespace(is_authenticated=False),
        }
        consumer.channel_layer = AsyncMock()
        consumer.channel_name = "test-channel"
        consumer.close = AsyncMock()

        await consumer.connect()

        consumer.close.assert_awaited_once_with(code=4401)

    async def test_notification_created_sends_json_payload(self) -> None:
        consumer = NotificationConsumer()
        consumer.send_json = AsyncMock()

        await consumer.notification_created(
            {"event": "notification.created", "data": {"id": "1", "type": "task_assigned"}}
        )

        consumer.send_json.assert_awaited_once_with(
            {"event": "notification.created", "data": {"id": "1", "type": "task_assigned"}}
        )
