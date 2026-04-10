from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import serializers

from apps.audit_logs.serializers import AuditLogListSerializer
from apps.memberships.models import Membership
from apps.tasks.models import (
    AutomationRule,
    FavoriteTask,
    GuestTaskAccess,
    Milestone,
    RecentTaskVisit,
    SavedTaskView,
    Task,
    TaskChecklistItem,
    TaskDependency,
    TaskLabel,
    TaskTemplate,
    TaskWatcher,
    TimeEntry,
)
from apps.tasks.services import (
    create_task,
    create_task_from_template,
    create_task_label,
    create_task_template,
    update_task,
    validate_task_labels,
)
from apps.teams.models import Team
from apps.teams.services import ensure_personal_workspace

User = get_user_model()


class TaskUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "name", "email", "avatar")
        read_only_fields = fields


class MilestoneSerializer(serializers.ModelSerializer):
    team = serializers.UUIDField(source="team_id", read_only=True)
    created_by = serializers.UUIDField(source="created_by_id", read_only=True, allow_null=True)
    progress = serializers.SerializerMethodField()
    linked_tasks = serializers.SerializerMethodField()

    class Meta:
        model = Milestone
        fields = (
            "id",
            "title",
            "description",
            "status",
            "due_date",
            "team",
            "created_by",
            "created_at",
            "updated_at",
            "progress",
            "linked_tasks",
        )
        read_only_fields = fields

    def get_progress(self, obj: Milestone) -> dict:
        tasks = getattr(obj, "tasks", None)
        total = tasks.count() if hasattr(tasks, "count") else Task.objects.filter(milestone=obj).count()
        completed = (
            tasks.filter(status=Task.Status.DONE).count()
            if hasattr(tasks, "filter")
            else Task.objects.filter(milestone=obj, status=Task.Status.DONE).count()
        )
        percentage = 0 if total == 0 else round((completed / total) * 100, 1)
        return {"total": total, "completed": completed, "percentage": percentage}

    def get_linked_tasks(self, obj: Milestone) -> list[dict]:
        tasks = getattr(obj, "tasks", None)
        queryset = tasks.all() if hasattr(tasks, "all") else Task.objects.select_related("assigned_to").filter(milestone=obj)
        return [
            {
                "id": str(task.id),
                "title": task.title,
                "status": task.status,
                "assignee_name": getattr(task.assigned_to, "name", "") or getattr(task.assigned_to, "email", ""),
            }
            for task in queryset.order_by("-updated_at", "title")[:4]
        ]


class TaskDependencySerializer(serializers.ModelSerializer):
    from_task = serializers.UUIDField(source="from_task_id", read_only=True)
    to_task = serializers.UUIDField(source="to_task_id", read_only=True)
    from_task_title = serializers.CharField(source="from_task.title", read_only=True)
    to_task_title = serializers.CharField(source="to_task.title", read_only=True)
    from_task_status = serializers.CharField(source="from_task.status", read_only=True)
    to_task_status = serializers.CharField(source="to_task.status", read_only=True)

    class Meta:
        model = TaskDependency
        fields = (
            "id",
            "dependency_type",
            "from_task",
            "to_task",
            "from_task_title",
            "to_task_title",
            "from_task_status",
            "to_task_status",
            "created_at",
        )
        read_only_fields = fields


class TimeEntrySerializer(serializers.ModelSerializer):
    user = TaskUserSerializer(read_only=True)
    task = serializers.UUIDField(source="task_id", read_only=True)

    class Meta:
        model = TimeEntry
        fields = (
            "id",
            "task",
            "user",
            "start_time",
            "end_time",
            "duration_seconds",
            "notes",
            "created_at",
        )
        read_only_fields = fields


class AutomationRuleSerializer(serializers.ModelSerializer):
    team = serializers.UUIDField(source="team_id", read_only=True, allow_null=True)
    created_by = TaskUserSerializer(read_only=True)

    class Meta:
        model = AutomationRule
        fields = (
            "id",
            "name",
            "team",
            "trigger_type",
            "conditions",
            "action_type",
            "action_payload",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class GuestTaskAccessSerializer(serializers.ModelSerializer):
    task = serializers.UUIDField(source="task_id", read_only=True)
    invited_by = TaskUserSerializer(read_only=True)

    class Meta:
        model = GuestTaskAccess
        fields = (
            "id",
            "task",
            "email",
            "permission",
            "token",
            "expires_at",
            "revoked_at",
            "invited_by",
            "created_at",
        )
        read_only_fields = fields


class TaskLabelSerializer(serializers.ModelSerializer):
    team = serializers.UUIDField(source="team_id", read_only=True)

    class Meta:
        model = TaskLabel
        fields = ("id", "team", "name", "color", "created_at", "updated_at")
        read_only_fields = fields


class TaskChecklistItemSerializer(serializers.ModelSerializer):
    created_by = TaskUserSerializer(read_only=True)
    completed_by = TaskUserSerializer(read_only=True)

    class Meta:
        model = TaskChecklistItem
        fields = (
            "id",
            "title",
            "is_completed",
            "completed_at",
            "position",
            "created_by",
            "completed_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class TaskWatcherSerializer(serializers.ModelSerializer):
    user = TaskUserSerializer(read_only=True)

    class Meta:
        model = TaskWatcher
        fields = ("id", "user", "created_at", "updated_at")
        read_only_fields = fields


class TaskListSerializer(serializers.ModelSerializer):
    team = serializers.UUIDField(source="team_id", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    created_by = serializers.UUIDField(source="created_by_id", read_only=True)
    created_by_data = TaskUserSerializer(source="created_by", read_only=True)
    assigned_to = serializers.UUIDField(source="assigned_to_id", read_only=True, allow_null=True)
    assigned_to_data = TaskUserSerializer(source="assigned_to", read_only=True)
    milestone = serializers.UUIDField(source="milestone_id", read_only=True, allow_null=True)
    milestone_title = serializers.CharField(source="milestone.title", read_only=True, allow_null=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_blocked = serializers.SerializerMethodField()
    labels = TaskLabelSerializer(many=True, read_only=True)
    watcher_count = serializers.SerializerMethodField()
    checklist_summary = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    is_watching = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "status",
            "priority",
            "estimated_minutes",
            "planned_for_date",
            "start_at",
            "blocked_reason",
            "due_date",
            "recurrence_pattern",
            "recurrence_interval",
            "team",
            "team_name",
            "created_by",
            "created_by_data",
            "assigned_to",
            "assigned_to_data",
            "milestone",
            "milestone_title",
            "labels",
            "watcher_count",
            "checklist_summary",
            "is_favorite",
            "is_watching",
            "completed_at",
            "position",
            "is_overdue",
            "is_blocked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_watcher_count(self, obj):
        watchers = getattr(obj, "watchers", None)
        return watchers.count() if hasattr(watchers, "count") else obj.watchers.count()

    def get_checklist_summary(self, obj):
        items = list(getattr(obj, "checklist_items", []).all() if hasattr(getattr(obj, "checklist_items", None), "all") else getattr(obj, "checklist_items", []) or [])
        total = len(items) if items else obj.checklist_items.count()
        completed = len([item for item in items if item.is_completed]) if items else obj.checklist_items.filter(is_completed=True).count()
        return {"total": total, "completed": completed}

    def get_is_favorite(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        favorites = getattr(obj, "favorited_by", None)
        if hasattr(favorites, "all"):
            return any(str(favorite.user_id) == str(request.user.id) for favorite in favorites.all())
        return obj.favorited_by.filter(user=request.user).exists()

    def get_is_watching(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        watchers = getattr(obj, "watchers", None)
        if hasattr(watchers, "all"):
            return any(str(watcher.user_id) == str(request.user.id) for watcher in watchers.all())
        return obj.watchers.filter(user=request.user).exists()

    def get_is_blocked(self, obj):
        incoming = getattr(obj, "incoming_dependencies", None)
        if hasattr(incoming, "all"):
            dependencies = incoming.all()
        else:
            dependencies = TaskDependency.objects.filter(to_task=obj)
        for dependency in dependencies:
            if dependency.dependency_type == TaskDependency.DependencyType.BLOCKS:
                if dependency.from_task and dependency.from_task.status != Task.Status.DONE:
                    return True
        return False


class TaskDetailSerializer(TaskListSerializer):
    source_template = serializers.UUIDField(source="source_template_id", read_only=True, allow_null=True)
    last_status_changed_by = serializers.UUIDField(source="last_status_changed_by_id", read_only=True, allow_null=True)
    last_status_changed_by_data = TaskUserSerializer(source="last_status_changed_by", read_only=True)
    comment_count = serializers.SerializerMethodField()
    attachment_count = serializers.SerializerMethodField()
    checklist_items = TaskChecklistItemSerializer(many=True, read_only=True)
    watchers = TaskWatcherSerializer(many=True, read_only=True)
    dependencies_incoming = serializers.SerializerMethodField()
    dependencies_outgoing = serializers.SerializerMethodField()
    related_tasks = serializers.SerializerMethodField()
    milestone_detail = MilestoneSerializer(source="milestone", read_only=True)
    total_tracked_seconds = serializers.SerializerMethodField()

    class Meta(TaskListSerializer.Meta):
        fields = TaskListSerializer.Meta.fields + [
            "description",
            "is_archived",
            "archived_at",
            "source_template",
            "last_status_changed_at",
            "last_status_changed_by",
            "last_status_changed_by_data",
            "comment_count",
            "attachment_count",
            "checklist_items",
            "watchers",
            "dependencies_incoming",
            "dependencies_outgoing",
            "related_tasks",
            "milestone_detail",
            "total_tracked_seconds",
        ]
        read_only_fields = fields

    def get_comment_count(self, obj):
        return obj.comments.count()

    def get_attachment_count(self, obj):
        return obj.attachments.filter(is_deleted=False).count()

    def get_dependencies_incoming(self, obj):
        queryset = obj.incoming_dependencies.select_related("from_task").all()
        return TaskDependencySerializer(queryset, many=True).data

    def get_dependencies_outgoing(self, obj):
        queryset = obj.outgoing_dependencies.select_related("to_task").all()
        return TaskDependencySerializer(queryset, many=True).data

    def get_related_tasks(self, obj):
        related = TaskDependency.objects.filter(
            dependency_type=TaskDependency.DependencyType.RELATED,
        ).filter(models.Q(from_task=obj) | models.Q(to_task=obj)).select_related("from_task", "to_task")
        seen = []
        for dependency in related:
            other = dependency.to_task if dependency.from_task_id == obj.id else dependency.from_task
            if other is not None:
                seen.append(
                    {
                        "id": str(other.id),
                        "title": other.title,
                        "status": other.status,
                    }
                )
        return seen

    def get_total_tracked_seconds(self, obj):
        return obj.time_entries.aggregate(total=models.Sum("duration_seconds")).get("total") or 0


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
    team_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Task.Status.choices, required=False, default=Task.Status.TODO)
    priority = serializers.ChoiceField(choices=Task.Priority.choices, required=False, default=Task.Priority.MEDIUM)
    estimated_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    planned_for_date = serializers.DateField(required=False, allow_null=True)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    blocked_reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    recurrence_pattern = serializers.ChoiceField(choices=Task.Recurrence.choices, required=False, default=Task.Recurrence.NONE)
    recurrence_interval = serializers.IntegerField(required=False, min_value=1, default=1)
    assigned_to = serializers.UUIDField(required=False, allow_null=True)
    source_template = serializers.UUIDField(required=False, allow_null=True)
    labels = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    milestone_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long.")
        return value

    def validate(self, attrs):
        request_user = self.context["request"].user
        team_id = attrs.get("team_id")
        personal_membership = (
            Membership.objects.select_related("team")
            .filter(
                user=request_user,
                status=Membership.Status.ACTIVE,
                team__is_personal=True,
                team__is_archived=False,
            )
            .order_by("team__created_at")
            .first()
        )
        if personal_membership is None and request_user.account_type == User.AccountType.PERSONAL:
            personal_team = ensure_personal_workspace(user=request_user)
            personal_membership = (
                Membership.objects.select_related("team")
                .filter(
                    user=request_user,
                    status=Membership.Status.ACTIVE,
                    team=personal_team,
                    team__is_personal=True,
                    team__is_archived=False,
                )
                .first()
            )

        team = Team.objects.filter(pk=team_id, is_archived=False).first() if team_id else None
        membership = None
        if team is not None:
            membership = Membership.objects.filter(
                team=team,
                user=request_user,
                status=Membership.Status.ACTIVE,
            ).first()

        if team is None or membership is None:
            if personal_membership is not None:
                team = personal_membership.team
                membership = personal_membership
                attrs["team_id"] = team.id
            elif team is None:
                raise serializers.ValidationError({"team_id": "Selected team does not exist."})

        if not membership:
            raise serializers.ValidationError({"team_id": "You are not a member of this team."})

        assignee_id = attrs.get("assigned_to")
        if team.is_personal and assignee_id is not None:
            raise serializers.ValidationError({"assigned_to": "Personal tasks cannot be assigned to a teammate."})
        if (
            membership.role == Membership.Role.MEMBER
            and not team.is_personal
            and assignee_id is not None
            and str(assignee_id) != str(request_user.id)
        ):
            raise serializers.ValidationError(
                {"assigned_to": "Members can only assign new team tasks to themselves."}
            )
        if assignee_id is not None:
            assignee = User.objects.filter(pk=assignee_id, is_active=True).first()
            if not assignee or not Membership.objects.filter(
                team=team,
                user=assignee,
                status=Membership.Status.ACTIVE,
            ).exists():
                raise serializers.ValidationError({"assigned_to": "Selected user is not a member of this team."})
            attrs["assigned_to_user"] = assignee

        template_id = attrs.get("source_template")
        if template_id:
            template = TaskTemplate.objects.filter(pk=template_id, team=team).first()
            if not template:
                raise serializers.ValidationError({"source_template": "Selected template does not exist for this team."})
            attrs["source_template_object"] = template

        milestone_id = attrs.get("milestone_id")
        if milestone_id:
            milestone = Milestone.objects.filter(pk=milestone_id, team=team).first()
            if not milestone:
                raise serializers.ValidationError({"milestone_id": "Selected milestone does not exist for this team."})
            attrs["milestone_object"] = milestone

        attrs["labels_queryset"] = validate_task_labels(team=team, labels=attrs.get("labels", []))

        start_at = attrs.get("start_at")
        due_date = attrs.get("due_date")
        if start_at and due_date and due_date < start_at:
            raise serializers.ValidationError({"due_date": "Due time cannot be earlier than the start time."})

        attrs["team"] = team
        return attrs

    def create(self, validated_data):
        validated_data.pop("team_id", None)
        team = validated_data.pop("team")
        assignee = validated_data.pop("assigned_to_user", None)
        validated_data.pop("assigned_to", None)
        validated_data.pop("source_template", None)
        validated_data["source_template"] = validated_data.pop("source_template_object", None)
        validated_data["milestone"] = validated_data.pop("milestone_object", None)
        validated_data["labels"] = validated_data.pop("labels_queryset", [])
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
    estimated_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    planned_for_date = serializers.DateField(required=False, allow_null=True)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    blocked_reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    recurrence_pattern = serializers.ChoiceField(choices=Task.Recurrence.choices, required=False)
    recurrence_interval = serializers.IntegerField(required=False, min_value=1)
    labels = serializers.ListField(child=serializers.UUIDField(), required=False)
    position = serializers.IntegerField(required=False, min_value=0)
    milestone_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long.")
        return value

    def validate(self, attrs):
        task = self.context.get("task")
        if task is not None and "labels" in attrs:
            attrs["labels_queryset"] = validate_task_labels(team=task.team, labels=attrs.get("labels", []))
        if task is not None and "milestone_id" in attrs:
            milestone_id = attrs.get("milestone_id")
            if milestone_id is None:
                attrs["milestone_object"] = None
            else:
                milestone = Milestone.objects.filter(pk=milestone_id, team=task.team).first()
                if not milestone:
                    raise serializers.ValidationError({"milestone_id": "Selected milestone does not exist for this team."})
                attrs["milestone_object"] = milestone
        if task is not None:
            start_at = attrs.get("start_at", task.start_at)
            due_date = attrs.get("due_date", task.due_date)
            if start_at and due_date and due_date < start_at:
                raise serializers.ValidationError({"due_date": "Due time cannot be earlier than the start time."})
        return attrs


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
        if task.team.is_personal:
            raise serializers.ValidationError({"assigned_to": "Personal tasks cannot be assigned to a teammate."})
        assignee = User.objects.filter(pk=assignee_id, is_active=True).first()
        if not assignee or not Membership.objects.filter(
            team=task.team,
            user=assignee,
            status=Membership.Status.ACTIVE,
        ).exists():
            raise serializers.ValidationError({"assigned_to": "Selected user is not a member of this team."})

        attrs["assigned_to_user"] = assignee
        return attrs


class TaskDependencyCreateSerializer(serializers.Serializer):
    to_task_id = serializers.UUIDField()
    dependency_type = serializers.ChoiceField(choices=TaskDependency.DependencyType.choices, default=TaskDependency.DependencyType.BLOCKS)


class MilestoneCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Milestone.Status.choices, required=False, default=Milestone.Status.PLANNED)

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long.")
        return value


class MilestoneUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Milestone.Status.choices, required=False)

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long.")
        return value


class TimeEntryCreateSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class TimeEntryStopSerializer(serializers.Serializer):
    end_time = serializers.DateTimeField(required=False)


class AutomationRuleCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    trigger_type = serializers.ChoiceField(choices=AutomationRule.Trigger.choices)
    conditions = serializers.DictField(required=False, default=dict)
    action_type = serializers.ChoiceField(choices=AutomationRule.Action.choices)
    action_payload = serializers.DictField(required=False, default=dict)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Name must be at least 3 characters long.")
        return value


class AutomationRuleUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    conditions = serializers.DictField(required=False)
    action_type = serializers.ChoiceField(choices=AutomationRule.Action.choices, required=False)
    action_payload = serializers.DictField(required=False)
    is_active = serializers.BooleanField(required=False)

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError("Name must be at least 3 characters long.")
        return value


class GuestTaskAccessCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    permission = serializers.ChoiceField(choices=GuestTaskAccess.Permission.choices, default=GuestTaskAccess.Permission.VIEW)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class TaskTemplateSerializer(serializers.ModelSerializer):
    assigned_to = serializers.UUIDField(source="assigned_to_id", read_only=True, allow_null=True)
    assigned_to_data = TaskUserSerializer(source="assigned_to", read_only=True)
    created_by = serializers.UUIDField(source="created_by_id", read_only=True, allow_null=True)
    created_by_data = TaskUserSerializer(source="created_by", read_only=True)
    team = serializers.UUIDField(source="team_id", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = TaskTemplate
        fields = [
            "id",
            "name",
            "title",
            "description",
            "priority",
            "estimated_minutes",
            "planned_offset_days",
            "due_offset_days",
            "blocked_reason",
            "recurrence_pattern",
            "recurrence_interval",
            "assigned_to",
            "assigned_to_data",
            "created_by",
            "created_by_data",
            "team",
            "team_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TaskTemplateCreateSerializer(serializers.Serializer):
    team_id = serializers.UUIDField()
    name = serializers.CharField(max_length=120)
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=Task.Priority.choices, required=False, default=Task.Priority.MEDIUM)
    estimated_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    planned_offset_days = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    due_offset_days = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    blocked_reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    recurrence_pattern = serializers.ChoiceField(choices=Task.Recurrence.choices, required=False, default=Task.Recurrence.NONE)
    recurrence_interval = serializers.IntegerField(required=False, min_value=1, default=1)
    assigned_to = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        team = Team.objects.filter(pk=attrs["team_id"]).first()
        if not team:
            raise serializers.ValidationError({"team_id": "Selected team does not exist."})

        membership = Membership.objects.filter(team=team, user=self.context["request"].user, status=Membership.Status.ACTIVE).first()
        if not membership:
            raise serializers.ValidationError({"team_id": "You are not a member of this team."})

        assignee_id = attrs.get("assigned_to")
        if assignee_id is not None:
            assignee = User.objects.filter(pk=assignee_id, is_active=True).first()
            if not assignee or not Membership.objects.filter(team=team, user=assignee, status=Membership.Status.ACTIVE).exists():
                raise serializers.ValidationError({"assigned_to": "Selected user is not a member of this team."})
            attrs["assigned_to_user"] = assignee

        attrs["team"] = team
        return attrs

    def create(self, validated_data):
        validated_data.pop("team_id")
        team = validated_data.pop("team")
        assignee = validated_data.pop("assigned_to_user", None)
        validated_data.pop("assigned_to", None)
        return create_task_template(
            team=team,
            created_by=self.context["request"].user,
            assigned_to=assignee,
            **validated_data,
        )


class TaskTemplateInstantiateSerializer(serializers.Serializer):
    planned_for_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    assigned_to = serializers.UUIDField(required=False, allow_null=True)


class SavedTaskViewSerializer(serializers.ModelSerializer):
    team = serializers.UUIDField(source="team_id", read_only=True, allow_null=True)
    team_name = serializers.CharField(source="team.name", read_only=True, allow_null=True)

    class Meta:
        model = SavedTaskView
        fields = [
            "id",
            "name",
            "layout",
            "filters",
            "is_default",
            "is_shared",
            "is_pinned",
            "team",
            "team_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SavedTaskViewCreateSerializer(serializers.Serializer):
    team_id = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(max_length=120)
    layout = serializers.ChoiceField(choices=SavedTaskView.Layout.choices, required=False, default=SavedTaskView.Layout.LIST)
    filters = serializers.DictField(required=False, default=dict)
    is_default = serializers.BooleanField(required=False, default=False)
    is_shared = serializers.BooleanField(required=False, default=False)
    is_pinned = serializers.BooleanField(required=False, default=False)


class SavedTaskViewUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False)
    layout = serializers.ChoiceField(choices=SavedTaskView.Layout.choices, required=False)
    filters = serializers.DictField(required=False)
    is_default = serializers.BooleanField(required=False)
    is_shared = serializers.BooleanField(required=False)
    is_pinned = serializers.BooleanField(required=False)


class TaskLabelCreateSerializer(serializers.Serializer):
    team_id = serializers.UUIDField()
    name = serializers.CharField(max_length=60)
    color = serializers.CharField(max_length=16, required=False, default="#10b981")

    def validate(self, attrs):
        team = Team.objects.filter(pk=attrs["team_id"]).first()
        if not team:
            raise serializers.ValidationError({"team_id": "Selected team does not exist."})
        membership = Membership.objects.filter(team=team, user=self.context["request"].user, status=Membership.Status.ACTIVE).first()
        if not membership:
            raise serializers.ValidationError({"team_id": "You are not a member of this team."})
        attrs["team"] = team
        return attrs

    def create(self, validated_data):
        validated_data.pop("team_id")
        team = validated_data.pop("team")
        return create_task_label(team=team, created_by=self.context["request"].user, **validated_data)


class TaskChecklistItemCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)


class TaskChecklistItemUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    is_completed = serializers.BooleanField(required=False)
    position = serializers.IntegerField(required=False, min_value=0)


class TaskBulkActionSerializer(serializers.Serializer):
    task_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)
    action = serializers.ChoiceField(choices=[("assign", "Assign"), ("status", "Status"), ("archive", "Archive")])
    status = serializers.ChoiceField(choices=Task.Status.choices, required=False)
    assigned_to = serializers.UUIDField(required=False, allow_null=True)


class FavoriteTaskSerializer(serializers.ModelSerializer):
    task = TaskListSerializer(read_only=True)

    class Meta:
        model = FavoriteTask
        fields = ("id", "task", "created_at", "updated_at")
        read_only_fields = fields


class RecentTaskVisitSerializer(serializers.ModelSerializer):
    task = TaskListSerializer(read_only=True)

    class Meta:
        model = RecentTaskVisit
        fields = ("id", "task", "last_accessed_at")
        read_only_fields = fields


class TaskTimelineEntrySerializer(AuditLogListSerializer):
    class Meta(AuditLogListSerializer.Meta):
        fields = AuditLogListSerializer.Meta.fields + ["metadata"]
