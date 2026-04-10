from __future__ import annotations

from datetime import timedelta
from zoneinfo import available_timezones

from django.utils import timezone
from rest_framework import serializers

from apps.integrations.sms.services import default_sms_preferences, infer_phone_country_code, normalize_phone_number
from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.notifications.constants import NotificationType
from apps.users.models import PushDevice, User


def build_presence_payload(user: User) -> dict:
    last_seen_at = getattr(user, "last_seen_at", None)
    if not last_seen_at:
        return {"state": "offline", "label": "No recent activity", "last_seen_at": None}

    delta = timezone.now() - last_seen_at
    if delta <= timedelta(minutes=5):
        state = "online"
        label = "Online"
    elif delta <= timedelta(hours=1):
        state = "recent"
        label = "Active recently"
    elif delta <= timedelta(days=1):
        state = "away"
        label = "Seen today"
    else:
        state = "offline"
        label = "Offline"

    return {
        "state": state,
        "label": label,
        "last_seen_at": last_seen_at,
        "source": getattr(user, "last_seen_source", "") or "",
    }


class UserPublicSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    presence = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "name", "email", "avatar", "bio", "presence")
        read_only_fields = fields

    def get_email(self, obj: User) -> str:
        value = getattr(obj, "email", "") or ""
        return value if isinstance(value, str) else str(value)

    def get_avatar(self, obj: User) -> str:
        value = getattr(obj, "avatar", "") or ""
        return value if isinstance(value, str) else str(value)

    def get_bio(self, obj: User) -> str:
        value = getattr(obj, "bio", "") or ""
        return value if isinstance(value, str) else str(value)

    def get_presence(self, obj: User) -> dict:
        return build_presence_payload(obj)


class CurrentUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    timezone = serializers.SerializerMethodField()
    notification_preferences = serializers.SerializerMethodField()
    security_preferences = serializers.SerializerMethodField()
    sms_preferences = serializers.SerializerMethodField()
    profile_completion = serializers.SerializerMethodField()
    account_type = serializers.SerializerMethodField()
    default_team_id = serializers.SerializerMethodField()
    workspace_options = serializers.SerializerMethodField()
    has_team_workspaces = serializers.SerializerMethodField()
    primary_mode = serializers.SerializerMethodField()
    onboarding_completed = serializers.SerializerMethodField()
    theme_preference = serializers.SerializerMethodField()
    two_factor_status = serializers.SerializerMethodField()
    presence = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "phone_number",
            "phone_verified",
            "phone_country_code",
            "sms_opt_in",
            "name",
            "first_name",
            "last_name",
            "avatar",
            "bio",
            "timezone",
            "notification_preferences",
            "security_preferences",
            "sms_preferences",
            "auth_provider",
            "account_type",
            "primary_mode",
            "default_team_id",
            "workspace_options",
            "has_team_workspaces",
            "onboarding_completed",
            "theme_preference",
            "two_factor_status",
            "email_verified",
            "is_active",
            "is_staff",
            "last_login",
            "last_seen_at",
            "last_seen_source",
            "date_joined",
            "created_at",
            "updated_at",
            "profile_completion",
            "presence",
        )
        read_only_fields = (
            "id",
            "email",
            "phone_number",
            "phone_verified",
            "phone_country_code",
            "sms_opt_in",
            "auth_provider",
            "account_type",
            "primary_mode",
            "default_team_id",
            "workspace_options",
            "has_team_workspaces",
            "onboarding_completed",
            "theme_preference",
            "two_factor_status",
            "email_verified",
            "is_active",
            "is_staff",
            "last_login",
            "last_seen_at",
            "last_seen_source",
            "date_joined",
            "created_at",
            "updated_at",
            "profile_completion",
            "presence",
        )

    def get_name(self, obj: User) -> str:
        value = getattr(obj, "name", "") or ""
        return value if isinstance(value, str) else str(value)

    def get_first_name(self, obj: User) -> str:
        value = getattr(obj, "first_name", "") or ""
        return value if isinstance(value, str) else str(value)

    def get_last_name(self, obj: User) -> str:
        value = getattr(obj, "last_name", "") or ""
        return value if isinstance(value, str) else str(value)

    def get_avatar(self, obj: User) -> str:
        value = getattr(obj, "avatar", "") or ""
        return value if isinstance(value, str) else str(value)

    def get_bio(self, obj: User) -> str:
        value = getattr(obj, "bio", "") or ""
        return value if isinstance(value, str) else str(value)

    def get_timezone(self, obj: User) -> str:
        value = getattr(obj, "timezone", "UTC") or "UTC"
        return value if isinstance(value, str) else str(value)

    def get_notification_preferences(self, obj: User) -> dict:
        value = getattr(obj, "notification_preferences", {}) or {}
        if not isinstance(value, dict):
            value = {}

        channels = value.get("channels") if isinstance(value.get("channels"), dict) else {}

        def build_channel(channel_key: str) -> dict:
            channel_values = channels.get(channel_key) if isinstance(channels.get(channel_key), dict) else {}
            return {key: bool(channel_values.get(key, True)) for key in NotificationType.values}

        normalized = {
            "channels": {
                "in_app": build_channel("in_app"),
                "email": build_channel("email"),
            }
        }
        for key, item in value.items():
            if key not in normalized:
                normalized[key] = item
        return normalized

    def get_security_preferences(self, obj: User) -> dict:
        value = getattr(obj, "security_preferences", {}) or {}
        return value if isinstance(value, dict) else {}

    def get_sms_preferences(self, obj: User) -> dict:
        preferences = default_sms_preferences()
        preferences.update(getattr(obj, "sms_preferences", {}) or {})
        return preferences

    def get_profile_completion(self, obj: User) -> int:
        fields = [
            self.get_name(obj),
            self.get_first_name(obj),
            self.get_last_name(obj),
            self.get_avatar(obj),
            self.get_bio(obj),
            self.get_timezone(obj),
            getattr(obj, "phone_number", "") or "",
        ]
        filled = sum(1 for item in fields if item)
        return int((filled / len(fields)) * 100)

    def get_account_type(self, obj: User) -> str:
        return getattr(obj, "account_type", User.AccountType.PERSONAL)

    def get_primary_mode(self, obj: User) -> str:
        return getattr(obj, "primary_mode", self.get_account_type(obj))

    def get_onboarding_completed(self, obj: User) -> bool:
        return bool(getattr(obj, "onboarding_completed", False))

    def get_theme_preference(self, obj: User) -> str:
        return getattr(obj, "theme_preference", User.ThemePreference.SYSTEM)

    def get_two_factor_status(self, obj: User) -> str:
        return getattr(obj, "two_factor_status", User.TwoFactorStatus.DISABLED)

    def _ensure_personal_workspace(self, obj: User) -> None:
        if obj.account_type != User.AccountType.PERSONAL:
            return
        has_personal_workspace = Membership.objects.filter(
            user=obj,
            status=Membership.Status.ACTIVE,
            team__is_personal=True,
            team__is_archived=False,
        ).exists()
        if has_personal_workspace:
            return
        from apps.teams.services import ensure_personal_workspace

        ensure_personal_workspace(user=obj)

    def get_default_team_id(self, obj: User) -> str | None:
        self._ensure_personal_workspace(obj)
        memberships = (
            Membership.objects.filter(user=obj, status=Membership.Status.ACTIVE)
            .select_related("team")
            .order_by("team__created_at")
        )
        if obj.account_type == User.AccountType.TEAM:
            owned = memberships.filter(role=Membership.Role.ADMIN, team__created_by=obj).first()
            if owned:
                return str(owned.team_id)
            fallback = memberships.first()
            return str(fallback.team_id) if fallback else None

        personal = memberships.filter(team__is_personal=True).first()
        return str(personal.team_id) if personal else None

    def get_presence(self, obj: User) -> dict:
        return build_presence_payload(obj)

    def get_workspace_options(self, obj: User) -> list[dict]:
        self._ensure_personal_workspace(obj)
        memberships = (
            Membership.objects.filter(user=obj, status=Membership.Status.ACTIVE, team__is_archived=False)
            .select_related("team")
            .order_by("-team__is_personal", "team__name", "team__created_at")
        )
        options: list[dict] = []
        for membership in memberships:
            options.append(
                {
                    "id": str(membership.team_id),
                    "name": membership.team.name,
                    "is_personal": bool(membership.team.is_personal),
                    "allow_manager_invites": bool(membership.team.allow_manager_invites),
                    "my_role": membership.role,
                }
            )
        return options

    def get_has_team_workspaces(self, obj: User) -> bool:
        return Membership.objects.filter(
            user=obj,
            status=Membership.Status.ACTIVE,
            team__is_archived=False,
            team__is_personal=False,
        ).exists()


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
            "security_preferences",
            "sms_preferences",
            "theme_preference",
            "onboarding_completed",
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
        if "channels" in value:
            channels = value.get("channels")
            if not isinstance(channels, dict):
                raise serializers.ValidationError("Notification preferences channels must be an object.")
            normalized_channels = {}
            for channel_key in ("in_app", "email"):
                channel_values = channels.get(channel_key, {})
                if not isinstance(channel_values, dict):
                    raise serializers.ValidationError(f"Notification preferences {channel_key} must be an object.")
                normalized_channels[channel_key] = {str(key): bool(item) for key, item in channel_values.items()}
            normalized = {"channels": normalized_channels}
            for key, item in value.items():
                if key == "channels":
                    continue
                normalized[str(key)] = bool(item) if isinstance(item, bool) else item
            return normalized
        return {str(key): bool(item) for key, item in value.items()}

    def validate_security_preferences(self, value: dict) -> dict:
        if not isinstance(value, dict):
            raise serializers.ValidationError("Security preferences must be an object.")
        return value

    def validate_theme_preference(self, value: str) -> str:
        if value not in User.ThemePreference.values:
            raise serializers.ValidationError("Invalid theme preference.")
        return value

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
    presence = serializers.SerializerMethodField()
    team_memberships = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "phone_number",
            "phone_verified",
            "name",
            "avatar",
            "account_type",
            "email_verified",
            "is_active",
            "is_staff",
            "theme_preference",
            "two_factor_status",
            "last_seen_at",
            "presence",
            "team_memberships",
            "stats",
        )
        read_only_fields = fields

    def get_presence(self, obj: User) -> dict:
        return build_presence_payload(obj)

    def get_team_memberships(self, obj: User) -> list[dict]:
        memberships = getattr(obj, "team_memberships", None)
        if memberships is None:
            memberships = obj.team_memberships.select_related("team").filter(status=Membership.Status.ACTIVE)
        elif hasattr(memberships, "all"):
            memberships = memberships.select_related("team").filter(status=Membership.Status.ACTIVE)
        return [
            {
                "id": str(membership.id),
                "team_id": str(membership.team_id),
                "team_name": membership.team.name,
                "role": membership.role,
                "joined_at": membership.joined_at,
            }
            for membership in memberships
        ]

    def get_stats(self, obj: User) -> dict:
        queryset = Task.objects.filter(assigned_to=obj, is_archived=False)
        now = timezone.now()
        return {
            "assigned_tasks": queryset.count(),
            "completed_tasks": queryset.filter(status=Task.Status.DONE).count(),
            "overdue_tasks": queryset.exclude(status=Task.Status.DONE).filter(due_date__lt=now).count(),
        }


class AdminUserUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)
    theme_preference = serializers.ChoiceField(choices=User.ThemePreference.choices, required=False)
    two_factor_status = serializers.ChoiceField(choices=User.TwoFactorStatus.choices, required=False)
    sms_opt_in = serializers.BooleanField(required=False)
    phone_verified = serializers.BooleanField(required=False)


class PushDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushDevice
        fields = (
            "id",
            "platform",
            "token",
            "label",
            "app_version",
            "is_active",
            "last_seen_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class PushDeviceCreateSerializer(serializers.Serializer):
    platform = serializers.ChoiceField(choices=PushDevice.Platform.choices)
    token = serializers.CharField(max_length=255)
    label = serializers.CharField(required=False, allow_blank=True, max_length=120)
    app_version = serializers.CharField(required=False, allow_blank=True, max_length=40)


class PhoneSettingsSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True, allow_blank=False, max_length=32)
    phone_country_code = serializers.CharField(required=False, allow_blank=True, max_length=8)
    sms_opt_in = serializers.BooleanField(required=False)

    def validate_phone_number(self, value: str) -> str:
        try:
            return normalize_phone_number(value, self.initial_data.get("phone_country_code"))
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate(self, attrs: dict) -> dict:
        attrs["phone_country_code"] = attrs.get("phone_country_code") or infer_phone_country_code(attrs["phone_number"])
        return attrs


class NotificationPreferencesSerializer(serializers.Serializer):
    channels = serializers.DictField(required=False)
    mention_emails = serializers.BooleanField(required=False)
    task_assignment_emails = serializers.BooleanField(required=False)
    deadline_reminder_emails = serializers.BooleanField(required=False)
    comment_emails = serializers.BooleanField(required=False)
    invite_emails = serializers.BooleanField(required=False)
    admin_message_emails = serializers.BooleanField(required=False)
    mention_sms = serializers.BooleanField(required=False)
    task_assignment_sms = serializers.BooleanField(required=False)
    deadline_reminder_sms = serializers.BooleanField(required=False)
    invite_sms = serializers.BooleanField(required=False)
    broadcast_sms = serializers.BooleanField(required=False)

    def validate_channels(self, value: dict) -> dict:
        if not isinstance(value, dict):
            raise serializers.ValidationError("Channels must be an object.")

        normalized = {}
        for channel_key in ("in_app", "email"):
            channel_values = value.get(channel_key, {})
            if channel_values in (None, ""):
                channel_values = {}
            if not isinstance(channel_values, dict):
                raise serializers.ValidationError(f"{channel_key} preferences must be an object.")
            normalized[channel_key] = {
                notification_type: bool(channel_values.get(notification_type, True))
                for notification_type in NotificationType.values
            }
        return normalized

    def to_representation(self, instance):
        notification_preferences = getattr(instance, "notification_preferences", {}) or {}
        channels = notification_preferences.get("channels") if isinstance(notification_preferences.get("channels"), dict) else {}
        in_app = channels.get("in_app") if isinstance(channels.get("in_app"), dict) else {}
        email = channels.get("email") if isinstance(channels.get("email"), dict) else {}
        sms_preferences = default_sms_preferences()
        sms_preferences.update(getattr(instance, "sms_preferences", {}) or {})
        return {
            "channels": {
                "in_app": {key: bool(in_app.get(key, True)) for key in NotificationType.values},
                "email": {key: bool(email.get(key, True)) for key in NotificationType.values},
            },
            "mention_emails": bool(email.get(NotificationType.MENTIONED_IN_COMMENT, True)),
            "task_assignment_emails": bool(email.get(NotificationType.TASK_ASSIGNED, True)),
            "deadline_reminder_emails": bool(email.get(NotificationType.DEADLINE_APPROACHING, True)),
            "comment_emails": bool(email.get(NotificationType.COMMENT_POSTED, True)),
            "invite_emails": bool(email.get(NotificationType.TEAM_INVITE, True)),
            "admin_message_emails": bool(email.get(NotificationType.ADMIN_MESSAGE, True)),
            "mention_sms": bool(sms_preferences.get("mention_sms", True)),
            "task_assignment_sms": bool(sms_preferences.get("task_assignment_sms", True)),
            "deadline_reminder_sms": bool(sms_preferences.get("deadline_reminder_sms", True)),
            "invite_sms": bool(sms_preferences.get("invite_sms", True)),
            "broadcast_sms": bool(sms_preferences.get("broadcast_sms", True)),
        }


class PhoneVerificationRequestSerializer(serializers.Serializer):
    pass


class PhoneVerificationConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=4, max_length=6)


class CredentialChangeRequestSerializer(serializers.Serializer):
    credential_type = serializers.ChoiceField(choices=(("email", "Email"), ("phone", "Phone")))
    new_value = serializers.CharField(required=True, allow_blank=False, max_length=255)
    phone_country_code = serializers.CharField(required=False, allow_blank=True, max_length=8)

    def validate(self, attrs: dict) -> dict:
        credential_type = attrs["credential_type"]
        new_value = str(attrs["new_value"]).strip()
        if credential_type == "email":
            serializers.EmailField().run_validation(new_value)
            attrs["new_value"] = new_value.lower()
            attrs["phone_country_code"] = ""
            return attrs

        try:
            attrs["new_value"] = normalize_phone_number(new_value, attrs.get("phone_country_code"))
        except ValueError as exc:
            raise serializers.ValidationError({"new_value": str(exc)}) from exc
        attrs["phone_country_code"] = attrs.get("phone_country_code") or infer_phone_country_code(attrs["new_value"])
        return attrs


class CredentialChangeConfirmSerializer(serializers.Serializer):
    credential_type = serializers.ChoiceField(choices=(("email", "Email"), ("phone", "Phone")))
    code = serializers.CharField(min_length=4, max_length=6)
