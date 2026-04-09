from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from apps.users.permissions import IsConfiguredPlatformAdmin
from apps.common.api.mixins import PaginatedAPIViewMixin
from apps.common.responses import success_response
from apps.users.models import User
from apps.users.selectors import filter_admin_users
from apps.users.serializers import (
    AdminUserSearchSerializer,
    AdminUserUpdateSerializer,
    CredentialChangeConfirmSerializer,
    CredentialChangeRequestSerializer,
    CurrentUserSerializer,
    NotificationPreferencesSerializer,
    PhoneSettingsSerializer,
    PhoneVerificationConfirmSerializer,
    PhoneVerificationRequestSerializer,
    PushDeviceCreateSerializer,
    PushDeviceSerializer,
    UserProfileUpdateSerializer,
)
from apps.users.services import (
    get_user_profile,
    revoke_push_device,
    update_notification_preferences,
    update_phone_settings,
    update_user_profile,
    upsert_push_device,
)
from apps.authentication.services import (
    confirm_credential_change,
    confirm_phone_verification,
    request_credential_change,
    request_phone_verification,
)
from apps.authentication.throttles import PhoneVerificationThrottle


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @extend_schema(responses=CurrentUserSerializer)
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = CurrentUserSerializer(get_user_profile(user=request.user))
        return success_response(
            request=request,
            message="Profile retrieved successfully.",
            data=serializer.data,
        )

    @extend_schema(request=UserProfileUpdateSerializer, responses=CurrentUserSerializer)
    def patch(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = UserProfileUpdateSerializer(instance=request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = update_user_profile(user=request.user, data=serializer.validated_data, request=request)
        return success_response(
            request=request,
            message="Profile updated successfully.",
            data=CurrentUserSerializer(user).data,
        )


class UserPhoneSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=PhoneSettingsSerializer, responses=CurrentUserSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = PhoneSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_phone_number = serializer.validated_data["phone_number"]
        if request.user.phone_number and requested_phone_number != request.user.phone_number:
            raise serializers.ValidationError(
                {"phone_number": "Verify a new phone number before replacing your current sign-in details."}
            )
        user = update_phone_settings(user=request.user, **serializer.validated_data)
        return success_response(
            request=request,
            message="Phone settings saved successfully.",
            data=CurrentUserSerializer(user).data,
        )

    @extend_schema(request=PhoneSettingsSerializer, responses=CurrentUserSerializer)
    def patch(self, request, *args, **kwargs):  # type: ignore[override]
        return self.post(request, *args, **kwargs)


class NotificationPreferencesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=NotificationPreferencesSerializer)
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        return success_response(
            request=request,
            message="Notification preferences retrieved successfully.",
            data=NotificationPreferencesSerializer(request.user).data,
        )

    @extend_schema(request=NotificationPreferencesSerializer, responses=NotificationPreferencesSerializer)
    def patch(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = NotificationPreferencesSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = update_notification_preferences(user=request.user, data=serializer.validated_data)
        return success_response(
            request=request,
            message="Notification preferences updated successfully.",
            data=NotificationPreferencesSerializer(user).data,
        )


class CredentialChangeRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PhoneVerificationThrottle]

    @extend_schema(request=CredentialChangeRequestSerializer, responses=CurrentUserSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = CredentialChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_credential_change(
            user=request.user,
            credential_type=serializer.validated_data["credential_type"],
            new_value=serializer.validated_data["new_value"],
            phone_country_code=serializer.validated_data.get("phone_country_code", ""),
            actor=request.user,
        )
        return success_response(
            request=request,
            message="Verification code sent successfully.",
            data=CurrentUserSerializer(request.user).data,
        )


class CredentialChangeConfirmView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PhoneVerificationThrottle]

    @extend_schema(request=CredentialChangeConfirmSerializer, responses=CurrentUserSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = CredentialChangeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = confirm_credential_change(
            user=request.user,
            credential_type=serializer.validated_data["credential_type"],
            code=serializer.validated_data["code"],
        )
        return success_response(
            request=request,
            message="Credentials updated successfully.",
            data=CurrentUserSerializer(user).data,
        )


class PhoneVerificationRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PhoneVerificationThrottle]

    @extend_schema(request=PhoneVerificationRequestSerializer, responses=CurrentUserSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = PhoneVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_phone_verification(user=request.user, actor=request.user)
        return success_response(
            request=request,
            message="Verification code sent successfully.",
            data=CurrentUserSerializer(request.user).data,
        )


class PhoneVerificationConfirmView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [PhoneVerificationThrottle]

    @extend_schema(request=PhoneVerificationConfirmSerializer, responses=CurrentUserSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = PhoneVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = confirm_phone_verification(user=request.user, code=serializer.validated_data["code"])
        return success_response(
            request=request,
            message="Phone number verified successfully.",
            data=CurrentUserSerializer(user).data,
        )


class AdminUserSearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    account_type = serializers.ChoiceField(choices=User.AccountType.choices, required=False)
    team = serializers.UUIDField(required=False)


class AdminUserSearchView(PaginatedAPIViewMixin, APIView):
    permission_classes = [IsConfiguredPlatformAdmin]

    @extend_schema(parameters=[AdminUserSearchQuerySerializer], responses=AdminUserSearchSerializer(many=True))
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        query = str(request.query_params.get("q", "")).strip()
        is_active = request.query_params.get("is_active")
        queryset = filter_admin_users(
            query=query,
            is_active=is_active.lower() == "true" if is_active is not None else None,
            account_type=str(request.query_params.get("account_type", "")).strip(),
            team_id=str(request.query_params.get("team", "")).strip(),
        )

        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=AdminUserSearchSerializer,
            message="Users retrieved successfully.",
            serializer_context={},
        )


class AdminUserDetailView(APIView):
    permission_classes = [IsConfiguredPlatformAdmin]

    @extend_schema(responses=AdminUserSearchSerializer)
    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        user = get_object_or_404(filter_admin_users(), pk=pk)
        return success_response(
            request=request,
            message="User retrieved successfully.",
            data=AdminUserSearchSerializer(user).data,
        )

    @extend_schema(request=AdminUserUpdateSerializer, responses=AdminUserSearchSerializer)
    def patch(self, request, pk, *args, **kwargs):  # type: ignore[override]
        user = get_object_or_404(filter_admin_users(), pk=pk)
        serializer = AdminUserUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(user, field, value)
        user.save(update_fields=[*serializer.validated_data.keys(), "updated_at"])
        return success_response(
            request=request,
            message="User updated successfully.",
            data=AdminUserSearchSerializer(user).data,
        )


class PushDeviceListCreateView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        queryset = request.user.push_devices.order_by("-last_seen_at", "-created_at")
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=PushDeviceSerializer,
            message="Push devices retrieved successfully.",
        )

    @extend_schema(request=PushDeviceCreateSerializer, responses=PushDeviceSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = PushDeviceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = upsert_push_device(user=request.user, **serializer.validated_data)
        return success_response(
            request=request,
            message="Push device saved successfully.",
            data=PushDeviceSerializer(device).data,
        )


class PushDeviceDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, *args, **kwargs):  # type: ignore[override]
        device = get_object_or_404(request.user.push_devices, pk=pk)
        revoke_push_device(device=device)
        return success_response(
            request=request,
            message="Push device removed successfully.",
            data=None,
        )
