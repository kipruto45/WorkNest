from __future__ import annotations

from django.db import models
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from apps.common.api.mixins import PaginatedAPIViewMixin
from apps.common.responses import success_response
from apps.users.models import User
from apps.users.serializers import AdminUserSearchSerializer, CurrentUserSerializer, UserProfileUpdateSerializer
from apps.users.services import get_user_profile, update_user_profile


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


class AdminUserSearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


class AdminUserSearchView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(parameters=[AdminUserSearchQuerySerializer], responses=AdminUserSearchSerializer(many=True))
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        query = str(request.query_params.get("q", "")).strip()
        queryset = User.objects.filter(is_staff=False).order_by("name", "email")

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        if query:
            queryset = queryset.filter(
                models.Q(name__icontains=query)
                | models.Q(email__icontains=query)
                | models.Q(first_name__icontains=query)
                | models.Q(last_name__icontains=query)
            )

        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=AdminUserSearchSerializer,
            message="Users retrieved successfully.",
            serializer_context={},
        )
