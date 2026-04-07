from __future__ import annotations

from zoneinfo import available_timezones

from rest_framework import serializers

from apps.users.models import User


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "name", "avatar", "bio")
        read_only_fields = fields


class CurrentUserSerializer(serializers.ModelSerializer):
    profile_completion = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "name",
            "first_name",
            "last_name",
            "avatar",
            "bio",
            "timezone",
            "notification_preferences",
            "auth_provider",
            "email_verified",
            "is_active",
            "is_staff",
            "last_login",
            "date_joined",
            "created_at",
            "updated_at",
            "profile_completion",
        )
        read_only_fields = (
            "id",
            "email",
            "auth_provider",
            "email_verified",
            "is_active",
            "is_staff",
            "last_login",
            "date_joined",
            "created_at",
            "updated_at",
            "profile_completion",
        )

    def get_profile_completion(self, obj: User) -> int:
        fields = [obj.name, obj.first_name, obj.last_name, obj.avatar, obj.bio, obj.timezone]
        filled = sum(1 for item in fields if item)
        return int((filled / len(fields)) * 100)


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    avatar_file = serializers.FileField(required=False, allow_null=True, write_only=True)
    clear_avatar = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = User
        fields = (
            "name",
            "first_name",
            "last_name",
            "avatar",
            "avatar_file",
            "clear_avatar",
            "bio",
            "timezone",
            "notification_preferences",
        )

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long.")
        return value

    def validate_first_name(self, value: str) -> str:
        return value.strip()

    def validate_last_name(self, value: str) -> str:
        return value.strip()

    def validate_bio(self, value: str) -> str:
        if len(value) > 1000:
            raise serializers.ValidationError("Bio cannot exceed 1000 characters.")
        return value.strip()

    def validate_timezone(self, value: str) -> str:
        if value not in available_timezones():
            raise serializers.ValidationError("Invalid timezone.")
        return value

    def validate_notification_preferences(self, value: dict) -> dict:
        if not isinstance(value, dict):
            raise serializers.ValidationError("Notification preferences must be an object.")
        return {str(key): bool(item) for key, item in value.items()}

    def validate_avatar_file(self, value):
        if value is None:
            return value

        content_type = str(getattr(value, "content_type", "") or "").lower()
        if not content_type.startswith("image/"):
            raise serializers.ValidationError("Avatar must be an image file.")

        max_size = 5 * 1024 * 1024
        if getattr(value, "size", 0) > max_size:
            raise serializers.ValidationError("Avatar image cannot exceed 5 MB.")

        return value


class AdminUserSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "name",
            "avatar",
            "is_active",
            "is_staff",
        )
        read_only_fields = fields
