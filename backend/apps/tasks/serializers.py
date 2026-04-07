from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.tasks.services import create_task
from apps.teams.models import Team

User = get_user_model()


class TaskUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "name", "email", "avatar")
        read_only_fields = fields


class TaskListSerializer(serializers.ModelSerializer):
    team = serializers.UUIDField(source="team_id", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    created_by = serializers.UUIDField(source="created_by_id", read_only=True)
    created_by_data = TaskUserSerializer(source="created_by", read_only=True)
    assigned_to = serializers.UUIDField(source="assigned_to_id", read_only=True, allow_null=True)
    assigned_to_data = TaskUserSerializer(source="assigned_to", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "status",
            "priority",
            "due_date",
            "team",
            "team_name",
            "created_by",
            "created_by_data",
            "assigned_to",
            "assigned_to_data",
            "completed_at",
            "position",
            "is_overdue",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TaskDetailSerializer(TaskListSerializer):
    last_status_changed_by = serializers.UUIDField(source="last_status_changed_by_id", read_only=True, allow_null=True)
    last_status_changed_by_data = TaskUserSerializer(source="last_status_changed_by", read_only=True)
    comment_count = serializers.SerializerMethodField()
    attachment_count = serializers.SerializerMethodField()

    class Meta(TaskListSerializer.Meta):
        fields = TaskListSerializer.Meta.fields + [
            "description",
            "is_archived",
            "archived_at",
            "last_status_changed_at",
            "last_status_changed_by",
            "last_status_changed_by_data",
            "comment_count",
            "attachment_count",
        ]
        read_only_fields = fields

    def get_comment_count(self, obj):
        return obj.comments.count()

    def get_attachment_count(self, obj):
        return obj.attachments.filter(is_deleted=False).count()


class TaskBoardSerializer(serializers.ModelSerializer):
    assigned_to_data = TaskUserSerializer(source="assigned_to", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "status",
            "priority",
            "due_date",
            "assigned_to",
            "assigned_to_data",
            "position",
            "is_overdue",
        ]
        read_only_fields = fields


class TaskCreateSerializer(serializers.Serializer):
    team_id = serializers.UUIDField()
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Task.Status.choices, required=False, default=Task.Status.TODO)
    priority = serializers.ChoiceField(choices=Task.Priority.choices, required=False, default=Task.Priority.MEDIUM)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    assigned_to = serializers.UUIDField(required=False, allow_null=True)

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long.")
        return value

    def validate(self, attrs):
        team = Team.objects.filter(pk=attrs["team_id"]).first()
        if not team:
            raise serializers.ValidationError({"team_id": "Selected team does not exist."})

        membership = Membership.objects.filter(
            team=team,
            user=self.context["request"].user,
            status=Membership.Status.ACTIVE,
        ).first()
        if not membership:
            raise serializers.ValidationError({"team_id": "You are not a member of this team."})

        assignee_id = attrs.get("assigned_to")
        if assignee_id is not None:
            assignee = User.objects.filter(pk=assignee_id, is_active=True).first()
            if not assignee or not Membership.objects.filter(
                team=team,
                user=assignee,
                status=Membership.Status.ACTIVE,
            ).exists():
                raise serializers.ValidationError({"assigned_to": "Selected user is not a member of this team."})
            attrs["assigned_to_user"] = assignee

        attrs["team"] = team
        return attrs

    def create(self, validated_data):
        validated_data.pop("team_id")
        team = validated_data.pop("team")
        assignee = validated_data.pop("assigned_to_user", None)
        validated_data.pop("assigned_to", None)
        return create_task(
            team=team,
            created_by=self.context["request"].user,
            assigned_to=assignee,
            **validated_data,
        )


class TaskUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=Task.Priority.choices, required=False)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    position = serializers.IntegerField(required=False, min_value=0)

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long.")
        return value


class TaskStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Task.Status.choices)


class TaskAssignSerializer(serializers.Serializer):
    assigned_to = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        if "assigned_to" not in attrs:
            raise serializers.ValidationError({"assigned_to": "This field is required."})

        assignee_id = attrs.get("assigned_to")
        if assignee_id is None:
            attrs["assigned_to_user"] = None
            return attrs

        task = self.context["task"]
        assignee = User.objects.filter(pk=assignee_id, is_active=True).first()
        if not assignee or not Membership.objects.filter(
            team=task.team,
            user=assignee,
            status=Membership.Status.ACTIVE,
        ).exists():
            raise serializers.ValidationError({"assigned_to": "Selected user is not a member of this team."})

        attrs["assigned_to_user"] = assignee
        return attrs
