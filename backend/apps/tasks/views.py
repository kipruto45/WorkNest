from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView

from apps.common.api.mixins import PaginatedAPIViewMixin, PermissionEnforcerMixin
from apps.common.responses import success_response
from apps.memberships.models import Membership
from apps.tasks.models import Task
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
    get_my_tasks,
    get_overdue_tasks,
    get_saved_task_views,
    get_task_for_user,
    get_task_templates,
    get_user_membership_tasks,
)
from apps.tasks.serializers import (
    SavedTaskViewCreateSerializer,
    SavedTaskViewSerializer,
    TaskAssignSerializer,
    TaskBoardSerializer,
    TaskCreateSerializer,
    TaskDetailSerializer,
    TaskListSerializer,
    TaskTemplateCreateSerializer,
    TaskTemplateInstantiateSerializer,
    TaskTemplateSerializer,
    TaskStatusUpdateSerializer,
    TaskUpdateSerializer,
)
from apps.tasks.services import (
    archive_task,
    assign_task,
    change_task_status,
    create_saved_task_view,
    create_task_from_template,
    delete_task,
    update_task,
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
        serializer = TaskUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = update_task(task=task, actor=request.user, **serializer.validated_data)
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
