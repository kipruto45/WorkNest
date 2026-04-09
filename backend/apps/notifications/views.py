from __future__ import annotations

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from apps.common.api.mixins import PaginatedAPIViewMixin
from apps.common.responses import success_response
from apps.authentication.throttles import AdminSMSBroadcastThrottle
from apps.notifications.permissions import IsNotificationOwner
from apps.users.permissions import IsConfiguredPlatformAdmin
from apps.notifications.selectors import (
    get_admin_communication_by_id,
    get_admin_communications,
    get_notification_for_user,
    get_sms_delivery_log_by_id,
    get_sms_delivery_logs,
    get_unread_count,
    get_user_notifications,
)
from apps.notifications.serializers import (
    AdminCommunicationCreateSerializer,
    AdminCommunicationSerializer,
    AdminNotificationSendSerializer,
    NotificationDetailSerializer,
    NotificationListQuerySerializer,
    NotificationListSerializer,
    NotificationStateSerializer,
    SMSDeliverySerializer,
)
from apps.notifications.services import (
    create_admin_communication,
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
    permission_classes = [IsConfiguredPlatformAdmin]

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


class AdminCommunicationListCreateView(PaginatedAPIViewMixin, APIView):
    permission_classes = [IsConfiguredPlatformAdmin]
    throttle_classes = [AdminSMSBroadcastThrottle]

    @extend_schema(responses=AdminCommunicationSerializer(many=True))
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        queryset = get_admin_communications()
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=AdminCommunicationSerializer,
            message="Communications retrieved successfully.",
            serializer_context={},
        )

    @extend_schema(request=AdminCommunicationCreateSerializer, responses=AdminCommunicationSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = AdminCommunicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = create_admin_communication(
            actor=request.user,
            audience_type=serializer.validated_data["audience_type"],
            channel_type=serializer.validated_data["channel_type"],
            title=serializer.validated_data["title"],
            message=serializer.validated_data["message"],
            user_ids=serializer.validated_data.get("user_ids") or [],
            team_ids=serializer.validated_data.get("team_ids") or [],
            scheduled_for=serializer.validated_data.get("scheduled_for"),
            cta_label=serializer.validated_data.get("cta_label", ""),
            cta_link=serializer.validated_data.get("cta_link", ""),
            confirm_broadcast=serializer.validated_data.get("confirm_broadcast", False),
        )
        communication = result["communication"]
        return success_response(
            request=request,
            message="Communication sent successfully.",
            data=AdminCommunicationSerializer(communication).data,
            status_code=status.HTTP_201_CREATED,
        )


class AdminCommunicationDetailView(APIView):
    permission_classes = [IsConfiguredPlatformAdmin]

    @extend_schema(responses=AdminCommunicationSerializer)
    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        communication = get_admin_communication_by_id(communication_id=pk)
        if not communication:
            raise NotFound("Communication not found.")
        return success_response(
            request=request,
            message="Communication retrieved successfully.",
            data=AdminCommunicationSerializer(communication).data,
        )


class AdminSMSLogListView(PaginatedAPIViewMixin, APIView):
    permission_classes = [IsConfiguredPlatformAdmin]

    @extend_schema(responses=SMSDeliverySerializer(many=True))
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        return self.paginate_success_response(
            request=request,
            queryset=get_sms_delivery_logs(),
            serializer_class=SMSDeliverySerializer,
            message="SMS logs retrieved successfully.",
        )


class AdminSMSLogDetailView(APIView):
    permission_classes = [IsConfiguredPlatformAdmin]

    @extend_schema(responses=SMSDeliverySerializer)
    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        delivery = get_sms_delivery_log_by_id(delivery_id=pk)
        if not delivery:
            raise NotFound("SMS log not found.")
        return success_response(
            request=request,
            message="SMS log retrieved successfully.",
            data=SMSDeliverySerializer(delivery).data,
        )
