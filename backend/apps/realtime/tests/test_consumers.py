from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from apps.realtime.consumers import NotificationConsumer, TeamEventConsumer
from apps.realtime.constants import build_team_group_name, build_user_group_name


class NotificationConsumerTests(unittest.IsolatedAsyncioTestCase):
    async def test_connect_adds_authenticated_active_user_to_group(self) -> None:
        consumer = NotificationConsumer()
        consumer.scope = {
            "type": "websocket",
            "user": SimpleNamespace(is_authenticated=True, is_active=True, id="user-123"),
        }
        consumer.channel_layer = AsyncMock()
        consumer.channel_name = "test-channel"
        consumer.accept = AsyncMock()

        await consumer.connect()

        consumer.channel_layer.group_add.assert_awaited_once_with(build_user_group_name("user-123"), "test-channel")
        consumer.accept.assert_awaited_once()

    async def test_connect_rejects_unauthenticated_user(self) -> None:
        consumer = NotificationConsumer()
        consumer.scope = {
            "type": "websocket",
            "user": SimpleNamespace(is_authenticated=False, is_active=True),
        }
        consumer.channel_layer = AsyncMock()
        consumer.channel_name = "test-channel"
        consumer.close = AsyncMock()

        await consumer.connect()

        consumer.close.assert_awaited_once_with(code=4401)

    async def test_task_assigned_handler_sends_json_payload(self) -> None:
        consumer = NotificationConsumer()
        consumer.send_json = AsyncMock()

        await consumer.task_assigned({"event": "task.assigned", "data": {"task_id": "1"}})

        consumer.send_json.assert_awaited_once_with({"event": "task.assigned", "data": {"task_id": "1"}})


class TeamEventConsumerTests(unittest.IsolatedAsyncioTestCase):
    async def test_connect_adds_authorized_member_to_team_group(self) -> None:
        consumer = TeamEventConsumer()
        consumer.scope = {
            "type": "websocket",
            "user": SimpleNamespace(is_authenticated=True, is_active=True, id="user-123"),
            "url_route": {"kwargs": {"team_id": "team-123"}},
        }
        consumer.channel_layer = AsyncMock()
        consumer.channel_name = "test-channel"
        consumer.accept = AsyncMock()

        with patch("apps.realtime.consumers.can_connect_team_channel", return_value=True):
            await consumer.connect()

        consumer.channel_layer.group_add.assert_awaited_once_with(build_team_group_name("team-123"), "test-channel")
        consumer.accept.assert_awaited_once()

    async def test_connect_rejects_unauthorized_team_access(self) -> None:
        consumer = TeamEventConsumer()
        consumer.scope = {
            "type": "websocket",
            "user": SimpleNamespace(is_authenticated=True, is_active=True, id="user-123"),
            "url_route": {"kwargs": {"team_id": "team-123"}},
        }
        consumer.channel_layer = AsyncMock()
        consumer.channel_name = "test-channel"
        consumer.close = AsyncMock()

        with patch("apps.realtime.consumers.can_connect_team_channel", return_value=False):
            await consumer.connect()

        consumer.close.assert_awaited_once_with(code=4403)

    async def test_comment_created_handler_sends_json_payload(self) -> None:
        consumer = TeamEventConsumer()
        consumer.send_json = AsyncMock()

        await consumer.comment_created({"event": "comment.created", "data": {"comment_id": "1"}})

        consumer.send_json.assert_awaited_once_with({"event": "comment.created", "data": {"comment_id": "1"}})
