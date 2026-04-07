from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView

from apps.audit_logs.serializers import AuditLogListSerializer
from apps.common.api.mixins import PaginatedAPIViewMixin, PermissionEnforcerMixin
from apps.common.responses import success_response
from apps.memberships.models import Membership
from apps.tasks.models import Task, TaskChecklistItem
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
    get_saved_task_views,
    get_task_for_user,
    get_task_labels,
    get_task_timeline,
    get_task_watchers,
    get_task_templates,
    get_user_membership_tasks,
)
from apps.tasks.serializers import (
    FavoriteTaskSerializer,
    RecentTaskVisitSerializer,
    SavedTaskViewCreateSerializer,
    SavedTaskViewSerializer,
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
)
from apps.tasks.services import (
    add_task_watcher,
    archive_task,
    assign_task,
    bulk_update_tasks,
    change_task_status,
    create_checklist_item,
    create_saved_task_view,
    create_task_from_template,
    delete_checklist_item,
    delete_task,
    remove_task_watcher,
    toggle_favorite_task,
    touch_recent_task,
    update_task,
    update_checklist_item,
)
from apps.teams.models import Team


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
        )
        return success_response(
            request=request,
            message="Saved task view created successfully.",
            data=SavedTaskViewSerializer(saved_view, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
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
