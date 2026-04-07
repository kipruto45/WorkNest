from __future__ import annotations

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from apps.realtime.constants import SYSTEM_PONG_EVENT, build_team_group_name, build_user_group_name
from apps.realtime.permissions import can_connect_team_channel, can_connect_user_channel
from apps.realtime.presence import (
    register_team_connection,
    register_user_connection,
    unregister_team_connection,
    unregister_user_connection,
)


class BaseRealtimeConsumer(AsyncJsonWebsocketConsumer):
    async def _send_event(self, event: dict) -> None:
        await self.send_json({"event": event["event"], "data": event["data"]})

    async def receive_json(self, content, **kwargs) -> None:
        if content.get("type") == "ping":
            await self.send_json(
                {
                    "event": SYSTEM_PONG_EVENT,
                    "data": {"timestamp": timezone.now().isoformat()},
                }
            )

    async def notification_created(self, event) -> None:
        await self._send_event(event)

    async def notification_updated(self, event) -> None:
        await self._send_event(event)

    async def notification_deleted(self, event) -> None:
        await self._send_event(event)

    async def notification_unread_count(self, event) -> None:
        await self._send_event(event)

    async def task_created(self, event) -> None:
        await self._send_event(event)

    async def task_updated(self, event) -> None:
        await self._send_event(event)

    async def task_status_changed(self, event) -> None:
        await self._send_event(event)

    async def task_assigned(self, event) -> None:
        await self._send_event(event)

    async def task_archived(self, event) -> None:
        await self._send_event(event)

    async def task_deleted(self, event) -> None:
        await self._send_event(event)

    async def comment_created(self, event) -> None:
        await self._send_event(event)

    async def comment_updated(self, event) -> None:
        await self._send_event(event)

    async def comment_deleted(self, event) -> None:
        await self._send_event(event)

    async def team_invite_received(self, event) -> None:
        await self._send_event(event)


class NotificationConsumer(BaseRealtimeConsumer):
    async def connect(self) -> None:
        user = self.scope.get("user")
        if not can_connect_user_channel(user=user):
            await self.close(code=4401)
            return

        self.group_name = build_user_group_name(user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await sync_to_async(register_user_connection)(user_id=user.id)
        await self.accept()

    async def disconnect(self, code) -> None:
        group_name = getattr(self, "group_name", None)
        user = self.scope.get("user")
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)
        if can_connect_user_channel(user=user):
            await sync_to_async(unregister_user_connection)(user_id=user.id)


class TeamEventConsumer(BaseRealtimeConsumer):
    async def connect(self) -> None:
        user = self.scope.get("user")
        team_id = self.scope.get("url_route", {}).get("kwargs", {}).get("team_id")
        if not can_connect_user_channel(user=user):
            await self.close(code=4401)
            return
        if not team_id or not await database_sync_to_async(can_connect_team_channel)(user=user, team_id=team_id):
            await self.close(code=4403)
            return

        self.team_id = str(team_id)
        self.group_name = build_team_group_name(team_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await sync_to_async(register_team_connection)(team_id=self.team_id)
        await self.accept()

    async def disconnect(self, code) -> None:
        group_name = getattr(self, "group_name", None)
        team_id = getattr(self, "team_id", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)
        if team_id:
            await sync_to_async(unregister_team_connection)(team_id=team_id)
