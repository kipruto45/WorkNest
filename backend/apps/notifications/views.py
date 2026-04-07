from __future__ import annotations

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from apps.common.api.mixins import PaginatedAPIViewMixin
from apps.common.responses import success_response
from apps.notifications.permissions import IsNotificationOwner
from apps.notifications.selectors import get_notification_for_user, get_unread_count, get_user_notifications
from apps.notifications.serializers import (
    AdminNotificationSendSerializer,
    NotificationDetailSerializer,
    NotificationListQuerySerializer,
    NotificationListSerializer,
    NotificationStateSerializer,
)
from apps.notifications.services import (
    delete_notification,
    mark_all_notifications_read,
    mark_notification_as_read,
    mark_notification_as_unread,
    send_admin_notifications,
)


class NotificationListView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(parameters=[NotificationListQuerySerializer], responses=NotificationListSerializer(many=True))
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        queryset = get_user_notifications(
            user=request.user,
            is_read=request.query_params.get("is_read"),
            notification_type=request.query_params.get("type"),
            team_id=request.query_params.get("team"),
        )
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=NotificationListSerializer,
            message="Notifications retrieved successfully.",
            serializer_context={},
        )


class NotificationDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotificationOwner]

    @extend_schema(responses=NotificationDetailSerializer)
    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        notification = get_notification_for_user(notification_id=pk, user=request.user)
        if not notification:
            raise NotFound("Notification not found.")
        self.check_object_permissions(request, notification)
        return success_response(
            request=request,
            message="Notification retrieved successfully.",
            data=NotificationDetailSerializer(notification).data,
        )

    @extend_schema(responses=None)
    def delete(self, request, pk, *args, **kwargs):  # type: ignore[override]
        notification = get_notification_for_user(notification_id=pk, user=request.user)
        if not notification:
            raise NotFound("Notification not found.")
        self.check_object_permissions(request, notification)
        delete_notification(notification=notification)
        return success_response(
            request=request,
            message="Notification deleted successfully.",
            data=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )


class NotificationUnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=inline_serializer(
            name="NotificationUnreadCountResponse",
            fields={"unread_count": serializers.IntegerField()},
        )
    )
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        return success_response(
            request=request,
            message="Unread notification count retrieved successfully.",
            data={"unread_count": get_unread_count(user=request.user)},
        )


class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotificationOwner]

    @extend_schema(responses=NotificationStateSerializer)
    def patch(self, request, pk, *args, **kwargs):  # type: ignore[override]
        notification = get_notification_for_user(notification_id=pk, user=request.user)
        if not notification:
            raise NotFound("Notification not found.")
        self.check_object_permissions(request, notification)
        notification = mark_notification_as_read(notification=notification)
        return success_response(
            request=request,
            message="Notification marked as read.",
            data=NotificationStateSerializer(notification).data,
        )


class NotificationMarkUnreadView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsNotificationOwner]

    @extend_schema(responses=NotificationStateSerializer)
    def patch(self, request, pk, *args, **kwargs):  # type: ignore[override]
        notification = get_notification_for_user(notification_id=pk, user=request.user)
        if not notification:
            raise NotFound("Notification not found.")
        self.check_object_permissions(request, notification)
        notification = mark_notification_as_unread(notification=notification)
        return success_response(
            request=request,
            message="Notification marked as unread.",
            data=NotificationStateSerializer(notification).data,
        )


class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses=inline_serializer(
            name="NotificationMarkAllReadResponse",
            fields={
                "updated_count": serializers.IntegerField(),
                "unread_count": serializers.IntegerField(),
            },
        )
    )
    def patch(self, request, *args, **kwargs):  # type: ignore[override]
        updated_count = mark_all_notifications_read(user=request.user)
        return success_response(
            request=request,
            message="All notifications marked as read.",
            data={"updated_count": updated_count, "unread_count": get_unread_count(user=request.user)},
        )


class AdminNotificationSendView(APIView):
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(request=AdminNotificationSendSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = AdminNotificationSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = send_admin_notifications(
            actor=request.user,
            scope=serializer.validated_data["scope"],
            title=serializer.validated_data.get("title", ""),
            message=serializer.validated_data["message"],
            user_ids=serializer.validated_data.get("user_ids") or [],
        )
        return success_response(
            request=request,
            message="Notification sent successfully.",
            data=result,
            status_code=status.HTTP_201_CREATED,
        )
