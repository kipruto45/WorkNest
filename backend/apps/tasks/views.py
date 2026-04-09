from __future__ import annotations

import csv
import io
import secrets

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView

from apps.audit_logs.serializers import AuditLogListSerializer
from apps.common.api.mixins import PaginatedAPIViewMixin, PermissionEnforcerMixin
from apps.common.responses import success_response
from apps.memberships.models import Membership
from apps.tasks.models import (
    AutomationRule,
    GuestTaskAccess,
    Milestone,
    SavedTaskView,
    Task,
    TaskChecklistItem,
    TaskDependency,
    TimeEntry,
)
from apps.tasks.permissions import (
    CanArchiveTask,
    CanAssignTask,
    CanChangeTaskStatus,
    CanCreateTask,
    CanDeleteTask,
    CanEditTask,
    CanViewTask,
)
from apps.tasks.selectors import (
    filter_tasks,
    get_board_tasks,
    get_favorite_tasks,
    get_recent_task_visits,
    get_task_checklist_items,
    get_my_tasks,
    get_overdue_tasks,
    get_team_tasks,
    get_saved_task_views,
    get_milestones,
    get_time_entries_for_task,
    get_time_entries_for_user,
    get_automation_rules,
    get_guest_access_entries,
    get_task_for_user,
    get_task_labels,
    get_task_timeline,
    get_task_watchers,
    get_task_templates,
    get_user_membership_tasks,
)
from apps.tasks.serializers import (
    AutomationRuleCreateSerializer,
    AutomationRuleSerializer,
    AutomationRuleUpdateSerializer,
    FavoriteTaskSerializer,
    GuestTaskAccessCreateSerializer,
    GuestTaskAccessSerializer,
    MilestoneCreateSerializer,
    MilestoneSerializer,
    MilestoneUpdateSerializer,
    RecentTaskVisitSerializer,
    SavedTaskViewCreateSerializer,
    SavedTaskViewSerializer,
    SavedTaskViewUpdateSerializer,
    TaskDependencyCreateSerializer,
    TaskDependencySerializer,
    TaskAssignSerializer,
    TaskBoardSerializer,
    TaskBulkActionSerializer,
    TaskChecklistItemCreateSerializer,
    TaskChecklistItemSerializer,
    TaskChecklistItemUpdateSerializer,
    TaskCreateSerializer,
    TaskDetailSerializer,
    TaskLabelCreateSerializer,
    TaskLabelSerializer,
    TaskListSerializer,
    TaskTimelineEntrySerializer,
    TaskTemplateCreateSerializer,
    TaskTemplateInstantiateSerializer,
    TaskTemplateSerializer,
    TaskWatcherSerializer,
    TaskStatusUpdateSerializer,
    TaskUpdateSerializer,
    TimeEntryCreateSerializer,
    TimeEntrySerializer,
    TimeEntryStopSerializer,
)
from apps.tasks.services import (
    add_task_watcher,
    archive_task,
    assign_task,
    bulk_update_tasks,
    change_task_status,
    create_milestone,
    create_checklist_item,
    create_task,
    create_task_dependency,
    create_saved_task_view,
    create_time_entry,
    create_task_from_template,
    delete_checklist_item,
    delete_milestone,
    delete_task_dependency,
    delete_task,
    remove_task_watcher,
    start_time_entry,
    stop_time_entry,
    toggle_favorite_task,
    touch_recent_task,
    update_task,
    update_checklist_item,
    update_milestone,
    update_saved_task_view,
    delete_saved_task_view,
)
from apps.teams.models import Team
from apps.teams.permissions import require_team_admin, require_team_member


class TaskListCreateView(PaginatedAPIViewMixin, PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        queryset = filter_tasks(get_user_membership_tasks(request.user), request.query_params)
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=TaskListSerializer,
            message="Tasks retrieved successfully.",
        )

    @extend_schema(request=TaskCreateSerializer, responses=TaskDetailSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        self.enforce_permission(request=request, permission_class=CanCreateTask)
        serializer = TaskCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        return success_response(
            request=request,
            message="Task created successfully.",
            data=TaskDetailSerializer(task, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
        )


class TaskDetailView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_task(self, pk, user):
        return get_task_for_user(pk, user, include_archived=True)

    @extend_schema(responses=TaskDetailSerializer)
    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        task = self.get_task(pk, request.user)
        if not task:
            return success_response(
                request=request,
                message="Task not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self.enforce_permission(request=request, permission_class=CanViewTask, obj=task)
        touch_recent_task(task=task, user=request.user)
        return success_response(
            request=request,
            message="Task retrieved successfully.",
            data=TaskDetailSerializer(task, context={"request": request}).data,
        )

    @extend_schema(request=TaskUpdateSerializer, responses=TaskDetailSerializer)
    def patch(self, request, pk, *args, **kwargs):  # type: ignore[override]
        task = self.get_task(pk, request.user)
        if not task:
            return success_response(
                request=request,
                message="Task not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self.enforce_permission(request=request, permission_class=CanEditTask, obj=task)
        serializer = TaskUpdateSerializer(data=request.data, partial=True, context={"task": task})
        serializer.is_valid(raise_exception=True)
        update_payload = dict(serializer.validated_data)
        if "labels_queryset" in update_payload:
            update_payload["labels"] = update_payload.pop("labels_queryset")
        if "milestone_object" in update_payload:
            update_payload["milestone"] = update_payload.pop("milestone_object")
        task = update_task(task=task, actor=request.user, **update_payload)
        return success_response(
            request=request,
            message="Task updated successfully.",
            data=TaskDetailSerializer(task, context={"request": request}).data,
        )

    def delete(self, request, pk, *args, **kwargs):  # type: ignore[override]
        task = self.get_task(pk, request.user)
        if not task:
            return success_response(
                request=request,
                message="Task not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self.enforce_permission(request=request, permission_class=CanDeleteTask, obj=task)
        delete_task(task=task, actor=request.user)
        return success_response(
            request=request,
            message="Task deleted successfully.",
            data=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )


class TaskStatusView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=TaskStatusUpdateSerializer, responses=TaskDetailSerializer)
    def patch(self, request, pk, *args, **kwargs):  # type: ignore[override]
        task = get_task_for_user(pk, request.user, include_archived=True)
        if not task:
            return success_response(
                request=request,
                message="Task not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self.enforce_permission(request=request, permission_class=CanChangeTaskStatus, obj=task)
        serializer = TaskStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = change_task_status(task=task, new_status=serializer.validated_data["status"], changed_by=request.user)
        return success_response(
            request=request,
            message="Task status updated successfully.",
            data=TaskDetailSerializer(task, context={"request": request}).data,
        )


class TaskAssignView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=TaskAssignSerializer, responses=TaskDetailSerializer)
    def patch(self, request, pk, *args, **kwargs):  # type: ignore[override]
        task = get_task_for_user(pk, request.user, include_archived=True)
        if not task:
            return success_response(
                request=request,
                message="Task not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self.enforce_permission(request=request, permission_class=CanAssignTask, obj=task)
        serializer = TaskAssignSerializer(data=request.data, context={"task": task})
        serializer.is_valid(raise_exception=True)
        task = assign_task(task=task, user=serializer.validated_data["assigned_to_user"], actor=request.user)
        return success_response(
            request=request,
            message="Task assignment updated successfully.",
            data=TaskDetailSerializer(task, context={"request": request}).data,
        )


class TaskArchiveView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):  # type: ignore[override]
        task = get_task_for_user(pk, request.user, include_archived=True)
        if not task:
            return success_response(
                request=request,
                message="Task not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self.enforce_permission(request=request, permission_class=CanArchiveTask, obj=task)
        task = archive_task(task=task, actor=request.user)
        return success_response(
            request=request,
            message="Task archived successfully.",
            data=TaskDetailSerializer(task, context={"request": request}).data,
        )


class MyTasksView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        queryset = filter_tasks(get_my_tasks(request.user), request.query_params)
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=TaskListSerializer,
            message="My tasks retrieved successfully.",
        )


class TaskBoardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        team_id = request.query_params.get("team")
        if not team_id:
            raise ValidationError({"team": "This query parameter is required."})

        team = Team.objects.filter(
            pk=team_id,
            memberships__user=request.user,
            memberships__status=Membership.Status.ACTIVE,
            is_archived=False,
        ).first()
        if not team:
            return success_response(
                request=request,
                message="Team not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        board_tasks = get_board_tasks(team, request.user)
        board = {
            status_key: {
                "count": tasks.count(),
                "tasks": TaskBoardSerializer(tasks, many=True, context={"request": request}).data,
            }
            for status_key, tasks in board_tasks.items()
        }

        return success_response(
            request=request,
            message="Task board retrieved successfully.",
            data=board,
        )


class OverdueTasksView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        queryset = get_overdue_tasks(request.user)
        if team_id := request.query_params.get("team"):
            queryset = queryset.filter(team_id=team_id)
        queryset = queryset.order_by("due_date", "position", "-created_at")
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=TaskListSerializer,
            message="Overdue tasks retrieved successfully.",
        )


class TaskTemplateListCreateView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        queryset = get_task_templates(user=request.user, team_id=request.query_params.get("team"))
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=TaskTemplateSerializer,
            message="Task templates retrieved successfully.",
        )

    @extend_schema(request=TaskTemplateCreateSerializer, responses=TaskTemplateSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = TaskTemplateCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        template = serializer.save()
        return success_response(
            request=request,
            message="Task template created successfully.",
            data=TaskTemplateSerializer(template, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
        )


class TaskTemplateInstantiateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=TaskTemplateInstantiateSerializer, responses=TaskDetailSerializer)
    def post(self, request, pk, *args, **kwargs):  # type: ignore[override]
        template = get_task_templates(user=request.user).filter(pk=pk).first()
        if not template:
            return success_response(
                request=request,
                message="Task template not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = TaskTemplateInstantiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assigned_to = None
        assigned_to_id = serializer.validated_data.get("assigned_to")
        if assigned_to_id is not None:
            assigned_to = template.team.memberships.filter(user_id=assigned_to_id, status=Membership.Status.ACTIVE).select_related("user").first()
            assigned_to = assigned_to.user if assigned_to else None
            if serializer.validated_data.get("assigned_to") and assigned_to is None:
                raise ValidationError({"assigned_to": "Selected user is not an active member of this team."})

        task = create_task_from_template(
            template=template,
            actor=request.user,
            planned_for_date=serializer.validated_data.get("planned_for_date"),
            due_date=serializer.validated_data.get("due_date"),
            assigned_to=assigned_to,
        )
        return success_response(
            request=request,
            message="Task created from template successfully.",
            data=TaskDetailSerializer(task, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
        )


class SavedTaskViewListCreateView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        queryset = get_saved_task_views(
            user=request.user,
            team_id=request.query_params.get("team"),
            layout=request.query_params.get("layout"),
        )
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=SavedTaskViewSerializer,
            message="Saved task views retrieved successfully.",
        )

    @extend_schema(request=SavedTaskViewCreateSerializer, responses=SavedTaskViewSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = SavedTaskViewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        team = None
        team_id = serializer.validated_data.get("team_id")
        if team_id:
            team = Team.objects.filter(
                pk=team_id,
                memberships__user=request.user,
                memberships__status=Membership.Status.ACTIVE,
                is_archived=False,
            ).first()
            if team is None:
                raise ValidationError({"team_id": "Selected team does not exist or is not accessible."})

        saved_view = create_saved_task_view(
            user=request.user,
            team=team,
            name=serializer.validated_data["name"],
            layout=serializer.validated_data["layout"],
            filters=serializer.validated_data.get("filters") or {},
            is_default=serializer.validated_data.get("is_default", False),
            is_shared=serializer.validated_data.get("is_shared", False),
            is_pinned=serializer.validated_data.get("is_pinned", False),
        )
        return success_response(
            request=request,
            message="Saved task view created successfully.",
            data=SavedTaskViewSerializer(saved_view, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
        )


class SavedTaskViewDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_saved_view(self, view_id, user):
        return SavedTaskView.objects.filter(id=view_id, user=user).select_related("team").first()

    @extend_schema(responses=SavedTaskViewSerializer)
    def get(self, request, view_id, *args, **kwargs):  # type: ignore[override]
        saved_view = self.get_saved_view(view_id, request.user)
        if not saved_view:
            return success_response(
                request=request,
                message="Saved task view not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return success_response(
            request=request,
            message="Saved task view retrieved successfully.",
            data=SavedTaskViewSerializer(saved_view, context={"request": request}).data,
        )

    @extend_schema(request=SavedTaskViewUpdateSerializer, responses=SavedTaskViewSerializer)
    def patch(self, request, view_id, *args, **kwargs):  # type: ignore[override]
        saved_view = self.get_saved_view(view_id, request.user)
        if not saved_view:
            return success_response(
                request=request,
                message="Saved task view not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = SavedTaskViewUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_saved_task_view(saved_view=saved_view, data=serializer.validated_data)
        return success_response(
            request=request,
            message="Saved task view updated successfully.",
            data=SavedTaskViewSerializer(updated, context={"request": request}).data,
        )

    def delete(self, request, view_id, *args, **kwargs):  # type: ignore[override]
        saved_view = self.get_saved_view(view_id, request.user)
        if not saved_view:
            return success_response(
                request=request,
                message="Saved task view not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        delete_saved_task_view(saved_view=saved_view)
        return success_response(
            request=request,
            message="Saved task view deleted successfully.",
            data=None,
        )


class TaskLabelListCreateView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        queryset = get_task_labels(user=request.user, team_id=request.query_params.get("team"))
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=TaskLabelSerializer,
            message="Task labels retrieved successfully.",
        )

    @extend_schema(request=TaskLabelCreateSerializer, responses=TaskLabelSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = TaskLabelCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        label = serializer.save()
        return success_response(
            request=request,
            message="Task label created successfully.",
            data=TaskLabelSerializer(label, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
        )


class TaskChecklistListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_task(self, pk, user):
        task = get_task_for_user(pk, user, include_archived=True)
        if not task:
            raise ValidationError({"task": "Task not found."})
        return task

    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        task = self.get_task(pk, request.user)
        return success_response(
            request=request,
            message="Checklist items retrieved successfully.",
            data=TaskChecklistItemSerializer(get_task_checklist_items(task=task), many=True).data,
        )

    @extend_schema(request=TaskChecklistItemCreateSerializer, responses=TaskChecklistItemSerializer)
    def post(self, request, pk, *args, **kwargs):  # type: ignore[override]
        task = self.get_task(pk, request.user)
        serializer = TaskChecklistItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = create_checklist_item(task=task, title=serializer.validated_data["title"], created_by=request.user)
        return success_response(
            request=request,
            message="Checklist item created successfully.",
            data=TaskChecklistItemSerializer(item).data,
            status_code=status.HTTP_201_CREATED,
        )


class TaskChecklistDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=TaskChecklistItemUpdateSerializer, responses=TaskChecklistItemSerializer)
    def patch(self, request, checklist_id, *args, **kwargs):  # type: ignore[override]
        checklist_item = TaskChecklistItem.objects.select_related("task").filter(
            pk=checklist_id,
            task__team__memberships__user=request.user,
            task__team__memberships__status=Membership.Status.ACTIVE,
        ).first()
        if not checklist_item:
            return success_response(
                request=request,
                message="Checklist item not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        serializer = TaskChecklistItemUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        checklist_item = update_checklist_item(checklist_item, actor=request.user, **serializer.validated_data)
        return success_response(
            request=request,
            message="Checklist item updated successfully.",
            data=TaskChecklistItemSerializer(checklist_item).data,
        )

    def delete(self, request, checklist_id, *args, **kwargs):  # type: ignore[override]
        checklist_item = TaskChecklistItem.objects.select_related("task").filter(
            pk=checklist_id,
            task__team__memberships__user=request.user,
            task__team__memberships__status=Membership.Status.ACTIVE,
        ).first()
        if not checklist_item:
            return success_response(
                request=request,
                message="Checklist item not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        delete_checklist_item(item=checklist_item, actor=request.user)
        return success_response(
            request=request,
            message="Checklist item deleted successfully.",
            data=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )


class TaskWatcherView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        task = get_task_for_user(pk, request.user, include_archived=True)
        if not task:
            return success_response(request=request, message="Task not found.", data=None, status_code=status.HTTP_404_NOT_FOUND)
        return success_response(
            request=request,
            message="Task watchers retrieved successfully.",
            data=TaskWatcherSerializer(get_task_watchers(task=task), many=True).data,
        )

    def post(self, request, pk, *args, **kwargs):  # type: ignore[override]
        task = get_task_for_user(pk, request.user, include_archived=True)
        if not task:
            return success_response(request=request, message="Task not found.", data=None, status_code=status.HTTP_404_NOT_FOUND)
        watcher, created = add_task_watcher(task=task, user=request.user)
        return success_response(
            request=request,
            message="Watcher updated successfully.",
            data={"watching": True, "created": created, "watcher": TaskWatcherSerializer(watcher).data},
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, pk, *args, **kwargs):  # type: ignore[override]
        task = get_task_for_user(pk, request.user, include_archived=True)
        if not task:
            return success_response(request=request, message="Task not found.", data=None, status_code=status.HTTP_404_NOT_FOUND)
        removed = remove_task_watcher(task=task, user=request.user)
        return success_response(
            request=request,
            message="Watcher updated successfully.",
            data={"watching": False, "removed": removed},
        )


class TaskTimelineView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        task = get_task_for_user(pk, request.user, include_archived=True)
        if not task:
            return success_response(request=request, message="Task not found.", data=None, status_code=status.HTTP_404_NOT_FOUND)
        queryset = get_task_timeline(task=task)
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=TaskTimelineEntrySerializer,
            message="Task activity timeline retrieved successfully.",
        )


class TaskBulkActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=TaskBulkActionSerializer, responses=TaskDetailSerializer(many=True))
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = TaskBulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_ids = serializer.validated_data["task_ids"]
        tasks = list(get_user_membership_tasks(request.user, include_archived=True).filter(id__in=task_ids))
        if len(tasks) != len(set(map(str, task_ids))):
            raise ValidationError({"task_ids": "One or more tasks are not accessible."})
        if not tasks:
            raise ValidationError({"task_ids": "Select at least one task."})

        team_ids = {str(task.team_id) for task in tasks}
        if len(team_ids) != 1:
            raise ValidationError({"task_ids": "Bulk actions can only be applied to tasks from one team at a time."})

        assigned_to = None
        if "assigned_to" in serializer.validated_data:
            assigned_to_id = serializer.validated_data.get("assigned_to")
            if assigned_to_id is not None:
                assigned_to = Membership.objects.filter(
                    team=tasks[0].team,
                    user_id=assigned_to_id,
                    status=Membership.Status.ACTIVE,
                ).select_related("user").first()
                assigned_to = assigned_to.user if assigned_to else None
                if serializer.validated_data.get("assigned_to") and assigned_to is None:
                    raise ValidationError({"assigned_to": "Selected user is not an active team member."})

        updated_tasks = bulk_update_tasks(
            tasks=tasks,
            actor=request.user,
            action=serializer.validated_data["action"],
            status=serializer.validated_data.get("status"),
            assigned_to=assigned_to,
        )
        return success_response(
            request=request,
            message="Bulk action applied successfully.",
            data=TaskDetailSerializer(updated_tasks, many=True, context={"request": request}).data,
        )


class FavoriteTaskToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):  # type: ignore[override]
        task = get_task_for_user(pk, request.user, include_archived=True)
        if not task:
            return success_response(request=request, message="Task not found.", data=None, status_code=status.HTTP_404_NOT_FOUND)
        is_favorite = toggle_favorite_task(task=task, user=request.user)
        return success_response(
            request=request,
            message="Favorite state updated successfully.",
            data={"is_favorite": is_favorite},
        )


class FavoriteTaskListView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        queryset = get_favorite_tasks(user=request.user)
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=FavoriteTaskSerializer,
            message="Favorite tasks retrieved successfully.",
            serializer_context={"request": request},
        )


class RecentTaskListView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        queryset = get_recent_task_visits(user=request.user)
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=RecentTaskVisitSerializer,
            message="Recent tasks retrieved successfully.",
            serializer_context={"request": request},
        )


class TaskDependencyListCreateView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def resolve_task_id(*, task_id=None, pk=None):
        return task_id or pk

    def get_task(self, *, task_id, user):
        task = get_task_for_user(task_id, user, include_archived=True)
        if not task:
            raise ValidationError({"task": "Task not found."})
        return task

    def get(self, request, task_id=None, pk=None, *args, **kwargs):  # type: ignore[override]
        task = self.get_task(task_id=self.resolve_task_id(task_id=task_id, pk=pk), user=request.user)
        incoming = TaskDependency.objects.filter(to_task=task).select_related("from_task")
        outgoing = TaskDependency.objects.filter(from_task=task).select_related("to_task")
        return success_response(
            request=request,
            message="Task dependencies retrieved successfully.",
            data={
                "incoming": TaskDependencySerializer(incoming, many=True).data,
                "outgoing": TaskDependencySerializer(outgoing, many=True).data,
            },
        )

    @extend_schema(request=TaskDependencyCreateSerializer, responses=TaskDependencySerializer)
    def post(self, request, task_id=None, pk=None, *args, **kwargs):  # type: ignore[override]
        task = self.get_task(task_id=self.resolve_task_id(task_id=task_id, pk=pk), user=request.user)
        self.enforce_permission(request=request, permission_class=CanEditTask, obj=task)
        serializer = TaskDependencyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to_task = get_task_for_user(str(serializer.validated_data["to_task_id"]), request.user, include_archived=True)
        if not to_task:
            raise ValidationError({"to_task_id": "Selected task is not accessible."})
        dependency = create_task_dependency(
            from_task=task,
            to_task=to_task,
            dependency_type=serializer.validated_data["dependency_type"],
            actor=request.user,
        )
        return success_response(
            request=request,
            message="Task dependency created successfully.",
            data=TaskDependencySerializer(dependency).data,
            status_code=status.HTTP_201_CREATED,
        )


class TaskDependencyDetailView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, dependency_id, *args, **kwargs):  # type: ignore[override]
        dependency = TaskDependency.objects.select_related("from_task").filter(id=dependency_id).first()
        if not dependency:
            return success_response(
                request=request,
                message="Dependency not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self.enforce_permission(request=request, permission_class=CanEditTask, obj=dependency.from_task)
        delete_task_dependency(dependency=dependency, actor=request.user)
        return success_response(
            request=request,
            message="Task dependency removed successfully.",
            data=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )


class MilestoneListCreateView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        queryset = get_milestones(user=request.user, team_id=team_id)
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=MilestoneSerializer,
            message="Milestones retrieved successfully.",
        )

    @extend_schema(request=MilestoneCreateSerializer, responses=MilestoneSerializer)
    def post(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        team = Team.objects.filter(
            pk=team_id,
            memberships__user=request.user,
            memberships__status=Membership.Status.ACTIVE,
            is_archived=False,
        ).first()
        if not team:
            raise ValidationError({"team_id": "Selected team does not exist or is not accessible."})
        require_team_admin(team=team, user=request.user)
        serializer = MilestoneCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        milestone = create_milestone(
            team=team,
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            status=serializer.validated_data.get("status", Milestone.Status.PLANNED),
            due_date=serializer.validated_data.get("due_date"),
            actor=request.user,
        )
        return success_response(
            request=request,
            message="Milestone created successfully.",
            data=MilestoneSerializer(milestone).data,
            status_code=status.HTTP_201_CREATED,
        )


class MilestoneDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_milestone(self, *, team_id, milestone_id, user):
        milestone = Milestone.objects.select_related("team").filter(id=milestone_id, team_id=team_id).first()
        if not milestone:
            raise ValidationError({"milestone": "Milestone not found."})
        require_team_member(team=milestone.team, user=user)
        return milestone

    def get(self, request, team_id, milestone_id, *args, **kwargs):  # type: ignore[override]
        milestone = self.get_milestone(team_id=team_id, milestone_id=milestone_id, user=request.user)
        return success_response(
            request=request,
            message="Milestone retrieved successfully.",
            data=MilestoneSerializer(milestone).data,
        )

    @extend_schema(request=MilestoneUpdateSerializer, responses=MilestoneSerializer)
    def patch(self, request, team_id, milestone_id, *args, **kwargs):  # type: ignore[override]
        milestone = self.get_milestone(team_id=team_id, milestone_id=milestone_id, user=request.user)
        require_team_admin(team=milestone.team, user=request.user)
        serializer = MilestoneUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        milestone = update_milestone(milestone=milestone, actor=request.user, **serializer.validated_data)
        return success_response(
            request=request,
            message="Milestone updated successfully.",
            data=MilestoneSerializer(milestone).data,
        )

    def delete(self, request, team_id, milestone_id, *args, **kwargs):  # type: ignore[override]
        milestone = self.get_milestone(team_id=team_id, milestone_id=milestone_id, user=request.user)
        require_team_admin(team=milestone.team, user=request.user)
        delete_milestone(milestone=milestone, actor=request.user)
        return success_response(
            request=request,
            message="Milestone deleted successfully.",
            data=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )


class TimeEntryListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def resolve_task_id(*, task_id=None, pk=None):
        return task_id or pk

    def get_task(self, task_id, user):
        task = get_task_for_user(task_id, user, include_archived=True)
        if not task:
            raise ValidationError({"task": "Task not found."})
        return task

    def get(self, request, task_id=None, pk=None, *args, **kwargs):  # type: ignore[override]
        task = self.get_task(self.resolve_task_id(task_id=task_id, pk=pk), request.user)
        entries = get_time_entries_for_task(task=task)
        return success_response(
            request=request,
            message="Time entries retrieved successfully.",
            data=TimeEntrySerializer(entries, many=True).data,
        )

    @extend_schema(request=TimeEntryCreateSerializer, responses=TimeEntrySerializer)
    def post(self, request, task_id=None, pk=None, *args, **kwargs):  # type: ignore[override]
        task = self.get_task(self.resolve_task_id(task_id=task_id, pk=pk), request.user)
        serializer = TimeEntryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        start_time = serializer.validated_data.get("start_time") or timezone.now()
        entry = create_time_entry(
            task=task,
            user=request.user,
            start_time=start_time,
            end_time=serializer.validated_data.get("end_time"),
            notes=serializer.validated_data.get("notes", ""),
        )
        return success_response(
            request=request,
            message="Time entry created successfully.",
            data=TimeEntrySerializer(entry).data,
            status_code=status.HTTP_201_CREATED,
        )


class TimeEntryStartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, task_id=None, pk=None, *args, **kwargs):  # type: ignore[override]
        resolved_task_id = task_id or pk
        task = get_task_for_user(resolved_task_id, request.user, include_archived=True)
        if not task:
            raise ValidationError({"task": "Task not found."})
        entry = start_time_entry(task=task, user=request.user)
        return success_response(
            request=request,
            message="Timer started successfully.",
            data=TimeEntrySerializer(entry).data,
            status_code=status.HTTP_201_CREATED,
        )


class TimeEntryStopView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=TimeEntryStopSerializer, responses=TimeEntrySerializer)
    def post(self, request, entry_id, *args, **kwargs):  # type: ignore[override]
        entry = TimeEntry.objects.select_related("task").filter(id=entry_id, user=request.user).first()
        if not entry:
            raise ValidationError({"time_entry": "Time entry not found."})
        serializer = TimeEntryStopSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = stop_time_entry(entry=entry, end_time=serializer.validated_data.get("end_time"))
        return success_response(
            request=request,
            message="Timer stopped successfully.",
            data=TimeEntrySerializer(entry).data,
        )


class TimeEntrySummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        team_id = request.query_params.get("team")
        if team_id:
            entries = get_time_entries_for_user(user=request.user, team_id=team_id)
        else:
            entries = get_time_entries_for_user(user=request.user)
        total_seconds = sum(entry.duration_seconds for entry in entries)
        return success_response(
            request=request,
            message="Time tracking summary retrieved successfully.",
            data={"total_seconds": total_seconds, "entry_count": len(entries)},
        )


class AutomationRuleListCreateView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        queryset = get_automation_rules(user=request.user, team_id=team_id)
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=AutomationRuleSerializer,
            message="Automation rules retrieved successfully.",
        )

    @extend_schema(request=AutomationRuleCreateSerializer, responses=AutomationRuleSerializer)
    def post(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        team = Team.objects.filter(pk=team_id, is_archived=False).first()
        if not team:
            raise ValidationError({"team_id": "Selected team does not exist."})
        require_team_admin(team=team, user=request.user)
        serializer = AutomationRuleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule = AutomationRule.objects.create(
            team=team,
            name=serializer.validated_data["name"],
            trigger_type=serializer.validated_data["trigger_type"],
            conditions=serializer.validated_data.get("conditions", {}),
            action_type=serializer.validated_data["action_type"],
            action_payload=serializer.validated_data.get("action_payload", {}),
            is_active=serializer.validated_data.get("is_active", True),
            created_by=request.user,
        )
        return success_response(
            request=request,
            message="Automation rule created successfully.",
            data=AutomationRuleSerializer(rule).data,
            status_code=status.HTTP_201_CREATED,
        )


class AutomationRuleDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_rule(self, *, team_id, rule_id, user):
        rule = AutomationRule.objects.select_related("team").filter(id=rule_id, team_id=team_id).first()
        if not rule:
            raise ValidationError({"rule": "Automation rule not found."})
        require_team_admin(team=rule.team, user=user)
        return rule

    def get(self, request, team_id, rule_id, *args, **kwargs):  # type: ignore[override]
        rule = self.get_rule(team_id=team_id, rule_id=rule_id, user=request.user)
        return success_response(
            request=request,
            message="Automation rule retrieved successfully.",
            data=AutomationRuleSerializer(rule).data,
        )

    @extend_schema(request=AutomationRuleUpdateSerializer, responses=AutomationRuleSerializer)
    def patch(self, request, team_id, rule_id, *args, **kwargs):  # type: ignore[override]
        rule = self.get_rule(team_id=team_id, rule_id=rule_id, user=request.user)
        serializer = AutomationRuleUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(rule, field, value)
        rule.save(update_fields=[*serializer.validated_data.keys(), "updated_at"])
        return success_response(
            request=request,
            message="Automation rule updated successfully.",
            data=AutomationRuleSerializer(rule).data,
        )

    def delete(self, request, team_id, rule_id, *args, **kwargs):  # type: ignore[override]
        rule = self.get_rule(team_id=team_id, rule_id=rule_id, user=request.user)
        rule.delete()
        return success_response(
            request=request,
            message="Automation rule deleted successfully.",
            data=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )


class GuestTaskAccessListCreateView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def resolve_task_id(*, task_id=None, pk=None):
        return task_id or pk

    def get_task(self, task_id, user):
        task = get_task_for_user(task_id, user, include_archived=True)
        if not task:
            raise ValidationError({"task": "Task not found."})
        return task

    def get(self, request, task_id=None, pk=None, *args, **kwargs):  # type: ignore[override]
        task = self.get_task(self.resolve_task_id(task_id=task_id, pk=pk), request.user)
        self.enforce_permission(request=request, permission_class=CanEditTask, obj=task)
        entries = get_guest_access_entries(task=task)
        return success_response(
            request=request,
            message="Guest access entries retrieved successfully.",
            data=GuestTaskAccessSerializer(entries, many=True).data,
        )

    @extend_schema(request=GuestTaskAccessCreateSerializer, responses=GuestTaskAccessSerializer)
    def post(self, request, task_id=None, pk=None, *args, **kwargs):  # type: ignore[override]
        task = self.get_task(self.resolve_task_id(task_id=task_id, pk=pk), request.user)
        self.enforce_permission(request=request, permission_class=CanEditTask, obj=task)
        serializer = GuestTaskAccessCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = secrets.token_urlsafe(32)
        entry = GuestTaskAccess.objects.create(
            task=task,
            invited_by=request.user,
            email=serializer.validated_data["email"],
            permission=serializer.validated_data.get("permission", GuestTaskAccess.Permission.VIEW),
            expires_at=serializer.validated_data.get("expires_at"),
            token=token,
        )
        return success_response(
            request=request,
            message="Guest access created successfully.",
            data=GuestTaskAccessSerializer(entry).data,
            status_code=status.HTTP_201_CREATED,
        )


class GuestTaskAccessRevokeView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, access_id, *args, **kwargs):  # type: ignore[override]
        entry = GuestTaskAccess.objects.select_related("task").filter(id=access_id).first()
        if not entry:
            raise ValidationError({"guest": "Guest access not found."})
        self.enforce_permission(request=request, permission_class=CanEditTask, obj=entry.task)
        entry.revoked_at = timezone.now()
        entry.save(update_fields=["revoked_at"])
        return success_response(
            request=request,
            message="Guest access revoked successfully.",
            data=GuestTaskAccessSerializer(entry).data,
        )


class GuestTaskAccessDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token, *args, **kwargs):  # type: ignore[override]
        entry = GuestTaskAccess.objects.select_related("task", "task__team").filter(token=token, revoked_at__isnull=True).first()
        if not entry or (entry.expires_at and entry.expires_at < timezone.now()):
            return success_response(
                request=request,
                message="Guest access not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        task = entry.task
        return success_response(
            request=request,
            message="Guest task retrieved successfully.",
            data={
                "access": GuestTaskAccessSerializer(entry).data,
                "task": TaskDetailSerializer(task).data,
            },
        )


class GuestTaskCommentCreateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, token, *args, **kwargs):  # type: ignore[override]
        entry = GuestTaskAccess.objects.select_related("task").filter(token=token, revoked_at__isnull=True).first()
        if not entry or (entry.expires_at and entry.expires_at < timezone.now()):
            raise ValidationError({"guest": "Guest access not found."})
        if entry.permission != GuestTaskAccess.Permission.COMMENT:
            raise ValidationError({"guest": "Guest access does not allow comments."})
        content = str(request.data.get("content", "")).strip()
        if not content:
            raise ValidationError({"content": "This field may not be blank."})
        from apps.comments.models import Comment

        comment = Comment.objects.create(
            task=entry.task,
            author=None,
            content=content,
            guest_name=entry.email.split("@", 1)[0],
            guest_email=entry.email,
        )
        return success_response(
            request=request,
            message="Comment created successfully.",
            data={"id": str(comment.id), "content": comment.content, "created_at": comment.created_at},
            status_code=status.HTTP_201_CREATED,
        )


class TaskImportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        team_id = request.data.get("team_id")
        if not team_id:
            raise ValidationError({"team_id": "Team ID is required."})
        team = Team.objects.filter(pk=team_id, is_archived=False).first()
        if not team:
            raise ValidationError({"team_id": "Selected team does not exist."})
        require_team_admin(team=team, user=request.user)

        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "CSV file is required."})

        dry_run = str(request.query_params.get("dry_run", "")).lower() in {"1", "true", "yes"}
        decoded = upload.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))
        rows = []
        errors = []
        created_tasks = []

        for index, row in enumerate(reader, start=1):
            title = (row.get("title") or "").strip()
            if not title:
                errors.append({"row": index, "error": "Title is required."})
                continue
            assigned_email = (row.get("assigned_to") or "").strip().lower()
            assignee = None
            if assigned_email:
                assignee = team.memberships.filter(user__email__iexact=assigned_email, status=Membership.Status.ACTIVE).select_related("user").first()
                assignee = assignee.user if assignee else None
                if not assignee:
                    errors.append({"row": index, "error": f"Assignee {assigned_email} is not a team member."})
                    continue
            milestone_title = (row.get("milestone") or "").strip()
            milestone = None
            if milestone_title:
                milestone = Milestone.objects.filter(team=team, title__iexact=milestone_title).first()
                if not milestone:
                    errors.append({"row": index, "error": f"Milestone '{milestone_title}' not found."})
                    continue

            rows.append(
                {
                    "title": title,
                    "description": (row.get("description") or "").strip(),
                    "status": (row.get("status") or Task.Status.TODO).strip() or Task.Status.TODO,
                    "priority": (row.get("priority") or Task.Priority.MEDIUM).strip() or Task.Priority.MEDIUM,
                    "start_at": row.get("start_at") or None,
                    "due_date": row.get("due_date") or None,
                    "assigned_to": assignee,
                    "milestone": milestone,
                }
            )

        if dry_run:
            return success_response(
                request=request,
                message="Import preview generated successfully.",
                data={"rows": rows, "errors": errors},
            )

        for row in rows:
            task = create_task(
                team=team,
                title=row["title"],
                description=row["description"],
                status=row["status"],
                priority=row["priority"],
                start_at=row["start_at"],
                due_date=row["due_date"],
                assigned_to=row["assigned_to"],
                created_by=request.user,
                milestone=row["milestone"],
            )
            created_tasks.append(task)

        return success_response(
            request=request,
            message="Tasks imported successfully.",
            data={"created": len(created_tasks), "errors": errors},
            status_code=status.HTTP_201_CREATED,
        )


class TaskExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        team_id = request.query_params.get("team")
        if not team_id:
            raise ValidationError({"team": "Team ID is required."})
        team = Team.objects.filter(pk=team_id, is_archived=False).first()
        if not team:
            raise ValidationError({"team": "Selected team does not exist."})
        require_team_member(team=team, user=request.user)
        tasks = get_team_tasks(team, request.user)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["title", "description", "status", "priority", "start_at", "due_date", "assigned_to", "milestone"])
        for task in tasks:
            writer.writerow(
                [
                    task.title,
                    task.description,
                    task.status,
                    task.priority,
                    task.start_at.isoformat() if task.start_at else "",
                    task.due_date.isoformat() if task.due_date else "",
                    task.assigned_to.email if task.assigned_to else "",
                    task.milestone.title if task.milestone else "",
                ]
            )
        return success_response(
            request=request,
            message="Tasks exported successfully.",
            data={"content": output.getvalue(), "filename": f"{team.slug or team.name}-tasks.csv"},
        )
