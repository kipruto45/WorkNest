from __future__ import annotations

from rest_framework import serializers

from apps.tasks.models import Task


class CalendarScopeSerializer(serializers.Serializer):
    scope = serializers.ChoiceField(choices=["personal", "team"], default="personal")
    team_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs: dict) -> dict:
        scope = attrs.get("scope", "personal")
        team_id = attrs.get("team_id")
        if scope == "team" and not team_id:
            raise serializers.ValidationError({"team_id": "Team ID is required for team workspace actions."})
        if scope == "personal":
            attrs["team_id"] = None
        return attrs


class CalendarTaskSelectionSerializer(CalendarScopeSerializer):
    task_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=False,
    )
    include_my_tasks = serializers.BooleanField(required=False, default=False)
    status = serializers.ListField(
        child=serializers.ChoiceField(choices=Task.Status.choices),
        required=False,
        allow_empty=False,
    )
    priority = serializers.ListField(
        child=serializers.ChoiceField(choices=Task.Priority.choices),
        required=False,
        allow_empty=False,
    )
    assigned_to = serializers.UUIDField(required=False, allow_null=True)
    due_from = serializers.DateTimeField(required=False)
    due_to = serializers.DateTimeField(required=False)
    start_from = serializers.DateTimeField(required=False)
    start_to = serializers.DateTimeField(required=False)
    search = serializers.CharField(required=False, allow_blank=True)
    include_completed = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        due_from = attrs.get("due_from")
        due_to = attrs.get("due_to")
        if due_from and due_to and due_to < due_from:
            raise serializers.ValidationError({"due_to": "Due end date must be after due start date."})
        start_from = attrs.get("start_from")
        start_to = attrs.get("start_to")
        if start_from and start_to and start_to < start_from:
            raise serializers.ValidationError({"start_to": "Start end date must be after start start date."})
        return attrs


class CalendarImportPreviewSerializer(CalendarScopeSerializer):
    pass


class CalendarImportConfirmSerializer(serializers.Serializer):
    batch_id = serializers.UUIDField()
    event_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False,
    )
    import_all = serializers.BooleanField(required=False, default=False)
    default_status = serializers.ChoiceField(choices=Task.Status.choices, required=False, default=Task.Status.TODO)
    default_priority = serializers.ChoiceField(
        choices=Task.Priority.choices,
        required=False,
        default=Task.Priority.MEDIUM,
    )
    assign_to_me = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs: dict) -> dict:
        if not attrs.get("import_all") and not attrs.get("event_ids"):
            raise serializers.ValidationError({"event_ids": "Select at least one event or set import_all=true."})
        return attrs


class GoogleCalendarConnectSerializer(CalendarScopeSerializer):
    return_path = serializers.CharField(required=False, allow_blank=True, max_length=255)


class GoogleCalendarSelectSerializer(CalendarScopeSerializer):
    calendar_id = serializers.CharField(max_length=255)
    calendar_name = serializers.CharField(required=False, allow_blank=True, max_length=255)


class GoogleCalendarSyncSerializer(CalendarTaskSelectionSerializer):
    calendar_id = serializers.CharField(required=False, allow_blank=True, max_length=255)


class GoogleCalendarImportPreviewSerializer(CalendarScopeSerializer):
    max_results = serializers.IntegerField(required=False, min_value=1, max_value=250, default=50)
    time_min = serializers.DateTimeField(required=False)
    time_max = serializers.DateTimeField(required=False)

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        time_min = attrs.get("time_min")
        time_max = attrs.get("time_max")
        if time_min and time_max and time_max < time_min:
            raise serializers.ValidationError({"time_max": "time_max must be later than time_min."})
        return attrs
