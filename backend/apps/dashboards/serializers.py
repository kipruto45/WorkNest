from __future__ import annotations

from rest_framework import serializers

from apps.notifications.serializers import NotificationListSerializer
from apps.tasks.constants import TASK_ORDERING_FIELDS
from apps.tasks.models import Task
from apps.tasks.serializers import TaskListSerializer
from apps.teams.serializers import TeamAnnouncementSerializer


class StrictQuerySerializer(serializers.Serializer):
    def validate(self, attrs):
        allowed_fields = set(self.fields.keys())
        unexpected = sorted(set(self.initial_data.keys()) - allowed_fields)
        if unexpected:
            raise serializers.ValidationError(
                {field: "This query parameter is not supported." for field in unexpected}
            )
        return attrs


class DashboardTaskListQuerySerializer(StrictQuerySerializer):
    team = serializers.UUIDField(required=False)
    status = serializers.ChoiceField(choices=Task.Status.choices, required=False)
    priority = serializers.ChoiceField(choices=Task.Priority.choices, required=False)
    overdue = serializers.BooleanField(required=False)
    due_date_from = serializers.DateTimeField(required=False)
    due_date_to = serializers.DateTimeField(required=False)
    ordering = serializers.ChoiceField(choices=sorted(TASK_ORDERING_FIELDS), required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        due_date_from = attrs.get("due_date_from")
        due_date_to = attrs.get("due_date_to")
        if due_date_from and due_date_to and due_date_from > due_date_to:
            raise serializers.ValidationError({"due_date_to": "Must be on or after due_date_from."})
        return attrs


class DashboardCalendarQuerySerializer(StrictQuerySerializer):
    start = serializers.DateTimeField(required=False)
    end = serializers.DateTimeField(required=False)
    status = serializers.ChoiceField(choices=Task.Status.choices, required=False)
    priority = serializers.ChoiceField(choices=Task.Priority.choices, required=False)
    assignee = serializers.UUIDField(required=False)
    team = serializers.UUIDField(required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        start = attrs.get("start")
        end = attrs.get("end")
        if start and end and start > end:
            raise serializers.ValidationError({"end": "Must be on or after start."})
        return attrs


class DashboardUserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(allow_blank=True)
    email = serializers.EmailField()
    avatar = serializers.CharField(allow_blank=True, allow_null=True)


class DashboardTeamSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()


class DashboardCalendarEventSerializer(serializers.ModelSerializer):
    task_id = serializers.UUIDField(source="id", read_only=True)
    assignee = DashboardUserSummarySerializer(source="assigned_to", read_only=True, allow_null=True)
    team = DashboardTeamSummarySerializer(read_only=True)

    class Meta:
        model = Task
        fields = (
            "task_id",
            "title",
            "due_date",
            "status",
            "priority",
            "assignee",
            "team",
        )
        read_only_fields = fields


class StatusDistributionItemSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Task.Status.choices)
    label = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class PriorityDistributionItemSerializer(serializers.Serializer):
    priority = serializers.ChoiceField(choices=Task.Priority.choices)
    label = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class MemberActivitySerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.EmailField()
    avatar = serializers.CharField(allow_blank=True, allow_null=True)
    role = serializers.CharField()
    assigned_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    open_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    comment_count = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    last_activity_at = serializers.DateTimeField(allow_null=True)


class WorkloadDistributionSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.EmailField()
    avatar = serializers.CharField(allow_blank=True, allow_null=True)
    assigned_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    open_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    completion_rate = serializers.FloatField()


class PersonalDashboardSummarySerializer(serializers.Serializer):
    summary = serializers.DictField()
    status_distribution = StatusDistributionItemSerializer(many=True)
    priority_distribution = PriorityDistributionItemSerializer(many=True)
    recent_activity = NotificationListSerializer(many=True)


class TeamDashboardSummarySerializer(serializers.Serializer):
    summary = serializers.DictField()
    status_distribution = StatusDistributionItemSerializer(many=True)
    priority_distribution = PriorityDistributionItemSerializer(many=True)
    member_activity = MemberActivitySerializer(many=True)


class MemberSnapshotSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.EmailField()
    avatar = serializers.CharField(allow_blank=True, allow_null=True)
    role = serializers.CharField()
    assigned_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    open_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    comment_count = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    last_activity_at = serializers.DateTimeField(allow_null=True)


class TeamMemberOverviewSerializer(serializers.Serializer):
    team_context = serializers.DictField()
    welcome = serializers.DictField()
    my_progress = serializers.DictField()
    my_assigned_tasks = TaskListSerializer(many=True)
    due_today = TaskListSerializer(many=True)
    due_soon = TaskListSerializer(many=True)
    overdue = TaskListSerializer(many=True)
    calendar_preview = DashboardCalendarEventSerializer(many=True)
    recent_activity = NotificationListSerializer(many=True)
    notifications_preview = NotificationListSerializer(many=True)
    notifications_unread_count = serializers.IntegerField()
    members_snapshot = MemberSnapshotSerializer(many=True)
    latest_announcement = TeamAnnouncementSerializer(allow_null=True)
    announcements_count = serializers.IntegerField()


class AdminGrowthPointSerializer(serializers.Serializer):
    label = serializers.CharField()
    date = serializers.DateField()
    count = serializers.IntegerField()


class AdminActivityUserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.EmailField()
    actions = serializers.IntegerField()
    last_seen = serializers.DateTimeField()


class AdminRegistrationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(allow_blank=True)
    email = serializers.EmailField()
    created_at = serializers.DateTimeField()
    auth_provider = serializers.CharField()


class AdminTeamHealthSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    task_count = serializers.IntegerField()
    overdue_count = serializers.IntegerField()
    activity_count = serializers.IntegerField()
    updated_at = serializers.DateTimeField(allow_null=True)


class AdminEventSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    action = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    actor_name = serializers.CharField(allow_blank=True)
    team_name = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class AdminServiceStatusSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.CharField()
    tone = serializers.CharField()


class AdminNotificationDistributionSerializer(serializers.Serializer):
    type = serializers.CharField()
    count = serializers.IntegerField()


class AdminInsightSerializer(serializers.Serializer):
    severity = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    action_label = serializers.CharField()
    href = serializers.CharField()


class AdminDashboardSerializer(serializers.Serializer):
    overview = serializers.DictField()
    growth = serializers.DictField()
    user_activity = serializers.DictField()
    team_health = serializers.DictField()
    notifications = serializers.DictField()
    system_events = AdminEventSerializer(many=True)
    ops = serializers.DictField()
    insights = serializers.DictField()
