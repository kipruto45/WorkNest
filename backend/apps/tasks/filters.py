from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as filters

from apps.tasks.models import Task


class TaskFilter(filters.FilterSet):
    team = filters.UUIDFilter(field_name="team_id")
    status = filters.ChoiceFilter(choices=Task.Status.choices)
    priority = filters.ChoiceFilter(choices=Task.Priority.choices)
    assigned_to = filters.UUIDFilter(field_name="assigned_to_id")
    created_by = filters.UUIDFilter(field_name="created_by_id")
    is_archived = filters.BooleanFilter()
    overdue = filters.BooleanFilter(method="filter_overdue")
    search = filters.CharFilter(method="filter_search")
    due_date_from = filters.IsoDateTimeFilter(field_name="due_date", lookup_expr="gte")
    due_date_to = filters.IsoDateTimeFilter(field_name="due_date", lookup_expr="lte")

    class Meta:
        model = Task
        fields = [
            "team",
            "status",
            "priority",
            "assigned_to",
            "created_by",
            "is_archived",
            "overdue",
            "due_date_from",
            "due_date_to",
        ]

    def filter_overdue(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.exclude(status=Task.Status.DONE).filter(due_date__lt=timezone.now())

    def filter_search(self, queryset, name, value):
        return queryset.filter(Q(title__icontains=value) | Q(description__icontains=value))
