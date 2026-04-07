from django.urls import path

from apps.realtime.consumers import NotificationConsumer, TeamEventConsumer

app_name = "realtime"

websocket_urlpatterns = [
    path("ws/notifications/", NotificationConsumer.as_asgi()),
    path("ws/teams/<uuid:team_id>/events/", TeamEventConsumer.as_asgi()),
]
