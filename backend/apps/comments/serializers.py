from __future__ import annotations

from rest_framework import serializers

from apps.comments.constants import COMMENT_MAX_LENGTH
from apps.comments.models import Comment, CommentReaction, CommentVersion
from apps.comments.parsers import extract_mention_handles
from apps.comments.services import extract_mentions_from_comment, validate_comment_parent
from apps.users.serializers import UserPublicSerializer


class CommentAuthorSerializer(UserPublicSerializer):
    email = serializers.EmailField(read_only=True)

    class Meta(UserPublicSerializer.Meta):
        fields = ("id", "name", "email", "avatar", "bio")
        read_only_fields = fields


class MentionedUserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.EmailField()
    handle = serializers.CharField()


class CommentReactionSummarySerializer(serializers.Serializer):
    emoji = serializers.CharField()
    count = serializers.IntegerField()
    reacted = serializers.BooleanField()


class CommentThreadSerializer(serializers.ModelSerializer):
    task = serializers.UUIDField(source="task_id", read_only=True)
    author = serializers.UUIDField(source="author_id", read_only=True, allow_null=True)
    parent = serializers.UUIDField(source="parent_id", read_only=True, allow_null=True)
    author_data = CommentAuthorSerializer(source="author", read_only=True)
    replies = serializers.SerializerMethodField()
    mentioned_users = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    edit_history_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "task",
            "author",
            "author_data",
            "guest_name",
            "guest_email",
            "parent",
            "content",
            "is_edited",
            "edited_at",
            "is_deleted",
            "deleted_at",
            "mentioned_users",
            "reactions",
            "edit_history_count",
            "created_at",
            "updated_at",
            "replies",
        ]
        read_only_fields = fields

    def get_replies(self, obj):
        replies = getattr(obj, "replies", None)
        if replies is None:
            replies = obj.replies.select_related("author").order_by("created_at")
        return CommentReplyListSerializer(replies.all() if hasattr(replies, "all") else replies, many=True).data

    def get_mentioned_users(self, obj):
        users = extract_mentions_from_comment(content=obj.content, team=obj.task.team)
        return [
            {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "handle": user.email.split("@", 1)[0].lower(),
            }
            for user in users
        ]

    def get_reactions(self, obj):
        return serialize_comment_reactions(comment=obj, request=self.context.get("request"))

    def get_edit_history_count(self, obj):
        return getattr(obj, "versions_count", None) or obj.versions.count()


class CommentReplyListSerializer(serializers.ModelSerializer):
    task = serializers.UUIDField(source="task_id", read_only=True)
    author = serializers.UUIDField(source="author_id", read_only=True, allow_null=True)
    parent = serializers.UUIDField(source="parent_id", read_only=True, allow_null=True)
    author_data = CommentAuthorSerializer(source="author", read_only=True)
    mentioned_users = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    edit_history_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "task",
            "author",
            "author_data",
            "guest_name",
            "guest_email",
            "parent",
            "content",
            "is_edited",
            "edited_at",
            "is_deleted",
            "deleted_at",
            "mentioned_users",
            "reactions",
            "edit_history_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_mentioned_users(self, obj):
        users = extract_mentions_from_comment(content=obj.content, team=obj.task.team)
        return [
            {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "handle": user.email.split("@", 1)[0].lower(),
            }
            for user in users
        ]

    def get_reactions(self, obj):
        return serialize_comment_reactions(comment=obj, request=self.context.get("request"))

    def get_edit_history_count(self, obj):
        return getattr(obj, "versions_count", None) or obj.versions.count()


class CommentDetailSerializer(CommentThreadSerializer):
    pass


class CommentVersionSerializer(serializers.ModelSerializer):
    edited_by = UserPublicSerializer(read_only=True)

    class Meta:
        model = CommentVersion
        fields = (
            "id",
            "content",
            "edited_by",
            "edited_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=COMMENT_MAX_LENGTH)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Comment.objects.select_related("task"),
        required=False,
        allow_null=True,
    )

    def validate_content(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate(self, attrs):
        task = self.context["task"]
        parent = attrs.get("parent")
        validate_comment_parent(task=task, parent=parent)
        return attrs


class CommentUpdateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=COMMENT_MAX_LENGTH)

    def validate_content(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value


class CommentReplySerializer(serializers.Serializer):
    content = serializers.CharField(max_length=COMMENT_MAX_LENGTH)

    def validate_content(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value


def extract_mentions_from_content(content: str) -> list[str]:
    return extract_mention_handles(content)


class CommentReactionToggleSerializer(serializers.Serializer):
    emoji = serializers.ChoiceField(choices=CommentReaction.Emoji.choices)


def serialize_comment_reactions(*, comment: Comment, request=None) -> list[dict]:
    reactions = list(getattr(comment, "reactions", []).all() if hasattr(getattr(comment, "reactions", None), "all") else getattr(comment, "reactions", []) or [])
    if not reactions:
        return []

    current_user_id = None
    if request is not None and getattr(request, "user", None) is not None and request.user.is_authenticated:
        current_user_id = str(request.user.id)

    grouped: dict[str, dict] = {}
    for reaction in reactions:
        emoji = reaction.emoji
        if emoji not in grouped:
            grouped[emoji] = {"emoji": emoji, "count": 0, "reacted": False}
        grouped[emoji]["count"] += 1
        if current_user_id and str(reaction.user_id) == current_user_id:
            grouped[emoji]["reacted"] = True

    return sorted(grouped.values(), key=lambda item: (-item["count"], item["emoji"]))
