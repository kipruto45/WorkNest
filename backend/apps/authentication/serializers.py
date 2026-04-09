from __future__ import annotations

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from apps.users.serializers import CurrentUserSerializer
from apps.authentication.models import AuthSession
from apps.integrations.sms.services import infer_phone_country_code, normalize_phone_number

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})
    account_type = serializers.ChoiceField(choices=User.AccountType.choices, default=User.AccountType.PERSONAL)
    team_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    phone_country_code = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            "name",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "phone_country_code",
            "password",
            "password_confirm",
            "account_type",
            "team_name",
        )

    def validate_email(self, value: str) -> str:
        if not value:
            return ""
        normalized = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate_phone_number(self, value: str) -> str:
        if not value:
            return ""
        try:
            normalized = normalize_phone_number(value, self.initial_data.get("phone_country_code"))
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        if User.objects.filter(phone_number=normalized).exists():
            raise serializers.ValidationError("Phone number is already registered.")
        return normalized

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})

        name = attrs.get("name", "").strip()
        if len(name) < 2:
            raise serializers.ValidationError({"name": "Name must be at least 2 characters long."})

        account_type = attrs.get("account_type", User.AccountType.PERSONAL)
        team_name = (attrs.get("team_name") or "").strip()
        if account_type == User.AccountType.TEAM and not team_name:
            raise serializers.ValidationError({"team_name": "Team name is required for team accounts."})

        email = (attrs.get("email") or "").strip()
        phone_number = (attrs.get("phone_number") or "").strip()
        if not email and not phone_number:
            raise serializers.ValidationError({"email": "Enter an email or phone number to register."})
        if phone_number and not attrs.get("phone_country_code"):
            attrs["phone_country_code"] = infer_phone_country_code(phone_number)

        candidate = User(email=email or None, phone_number=phone_number or None, name=attrs["name"])
        try:
            password_validation.validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs


class LoginSerializer(serializers.Serializer):
    credential = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    remember_me = serializers.BooleanField(default=False, required=False)

    def validate(self, attrs: dict) -> dict:
        credential = (attrs.get("credential") or "").strip()
        email = (attrs.get("email") or "").strip()
        phone_number = (attrs.get("phone_number") or "").strip()
        resolved = credential or email or phone_number
        if not resolved:
            raise serializers.ValidationError({"credential": "Enter your email or phone number."})
        if phone_number and not credential:
            try:
                resolved = normalize_phone_number(phone_number)
            except ValueError as exc:
                raise serializers.ValidationError({"phone_number": str(exc)}) from exc
        attrs["credential"] = resolved
        return attrs


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=False)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})
    new_password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs: dict) -> dict:
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})

        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            raise serializers.ValidationError({"uid": "Invalid password reset link."})

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": "Invalid or expired password reset token."})

        password_validation.validate_password(attrs["new_password"], user)
        attrs["user"] = user
        return attrs


class GoogleOAuthConfigSerializer(serializers.Serializer):
    provider = serializers.CharField()
    enabled = serializers.BooleanField()
    login_url = serializers.URLField(allow_null=True)
    callback_url = serializers.URLField(allow_null=True)


class GoogleOAuthLoginSerializer(serializers.Serializer):
    provider = serializers.CharField()
    login_url = serializers.URLField()


class AuthTokensSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField(allow_null=True)
    refresh_expires_in = serializers.IntegerField()
    token_type = serializers.CharField()
    refresh_cookie_set = serializers.BooleanField()


class AuthTokenResponseSerializer(serializers.Serializer):
    user = CurrentUserSerializer()
    tokens = AuthTokensSerializer()


class EmailVerificationRequestSerializer(serializers.Serializer):
    token = serializers.CharField(allow_blank=False)


class AuthSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthSession
        fields = (
            "id",
            "session_key",
            "device_name",
            "ip_address",
            "user_agent",
            "last_seen_at",
            "expires_at",
            "revoked_at",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class GoogleAuthRequestSerializer(serializers.Serializer):
    credential = serializers.CharField(
        help_text="Google ID token (JWT) from Google Sign-In"
    )


class GoogleAuthResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.DictField(required=False)
    errors = serializers.DictField(required=False)
