from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from apps.comments.permissions import CanCreateComment, CanDeleteComment, CanEditOwnComment, IsTaskTeamMember
from apps.comments.selectors import build_comment_thread, get_comment_for_user, get_task_for_comment_access
from apps.comments.serializers import (
    CommentCreateSerializer,
    CommentDetailSerializer,
    CommentReactionToggleSerializer,
    CommentReplySerializer,
    CommentThreadSerializer,
    CommentUpdateSerializer,
    CommentVersionSerializer,
)
from apps.comments.services import create_comment, delete_comment, reply_to_comment, toggle_comment_reaction, update_comment
from apps.common.api.mixins import PaginatedAPIViewMixin, PermissionEnforcerMixin
from apps.common.responses import success_response


class CommentListCreateView(PaginatedAPIViewMixin, PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=CommentThreadSerializer(many=True))
    def get(self, request, task_id, *args, **kwargs):  # type: ignore[override]
        task = get_task_for_comment_access(task_id=task_id, user=request.user)
        if not task:
            return success_response(
                request=request,
                message="Task not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        queryset = build_comment_thread(task=task, user=request.user)
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=CommentThreadSerializer,
            message="Comments retrieved successfully.",
        )

    @extend_schema(request=CommentCreateSerializer, responses=CommentDetailSerializer)
    def post(self, request, task_id, *args, **kwargs):  # type: ignore[override]
        self.enforce_permission(request=request, permission_class=CanCreateComment)
        task = get_task_for_comment_access(task_id=task_id, user=request.user)
        if not task:
            return success_response(
                request=request,
                message="Task not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = CommentCreateSerializer(data=request.data, context={"task": task, "request": request})
        serializer.is_valid(raise_exception=True)
        comment, _mentions = create_comment(
            task=task,
            author=request.user,
            content=serializer.validated_data["content"],
            parent=serializer.validated_data.get("parent"),
        )
        return success_response(
            request=request,
            message="Comment added successfully.",
            data=CommentDetailSerializer(comment, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
        )


class CommentDetailView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_comment(self, pk, user):
        return get_comment_for_user(comment_id=pk, user=user)

    @extend_schema(responses=CommentDetailSerializer)
    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        comment = self.get_comment(pk, request.user)
        if not comment:
            return success_response(
                request=request,
                message="Comment not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self.enforce_permission(request=request, permission_class=IsTaskTeamMember, obj=comment)
        return success_response(
            request=request,
            message="Comment retrieved successfully.",
            data=CommentDetailSerializer(comment, context={"request": request}).data,
        )

    @extend_schema(request=CommentUpdateSerializer, responses=CommentDetailSerializer)
    def patch(self, request, pk, *args, **kwargs):  # type: ignore[override]
        comment = self.get_comment(pk, request.user)
        if not comment:
            return success_response(
                request=request,
                message="Comment not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self.enforce_permission(request=request, permission_class=CanEditOwnComment, obj=comment)
        serializer = CommentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment, _mentions = update_comment(comment=comment, content=serializer.validated_data["content"], actor=request.user)
        return success_response(
            request=request,
            message="Comment updated successfully.",
            data=CommentDetailSerializer(comment, context={"request": request}).data,
        )

    def delete(self, request, pk, *args, **kwargs):  # type: ignore[override]
        comment = self.get_comment(pk, request.user)
        if not comment:
            return success_response(
                request=request,
                message="Comment not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        self.enforce_permission(request=request, permission_class=CanDeleteComment, obj=comment)
        comment = delete_comment(comment=comment, actor=request.user)
        return success_response(
            request=request,
            message="Comment deleted successfully.",
            data=CommentDetailSerializer(comment, context={"request": request}).data,
        )


class CommentReplyView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=CommentReplySerializer, responses=CommentDetailSerializer)
    def post(self, request, pk, *args, **kwargs):  # type: ignore[override]
        parent_comment = get_comment_for_user(comment_id=pk, user=request.user)
        if not parent_comment:
            return success_response(
                request=request,
                message="Comment not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.enforce_permission(request=request, permission_class=IsTaskTeamMember, obj=parent_comment)
        serializer = CommentReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reply, _mentions = reply_to_comment(
            parent_comment=parent_comment,
            author=request.user,
            content=serializer.validated_data["content"],
        )
        return success_response(
            request=request,
            message="Reply added successfully.",
            data=CommentDetailSerializer(reply, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
        )


class CommentReactionToggleView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=CommentReactionToggleSerializer, responses=CommentDetailSerializer)
    def post(self, request, pk, *args, **kwargs):  # type: ignore[override]
        comment = get_comment_for_user(comment_id=pk, user=request.user)
        if not comment:
            return success_response(
                request=request,
                message="Comment not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.enforce_permission(request=request, permission_class=IsTaskTeamMember, obj=comment)
        serializer = CommentReactionToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        active, _reaction = toggle_comment_reaction(
            comment=comment,
            user=request.user,
            emoji=serializer.validated_data["emoji"],
        )
        refreshed_comment = get_comment_for_user(comment_id=pk, user=request.user)
        return success_response(
            request=request,
            message="Reaction updated successfully.",
            data={
                "active": active,
                "comment": CommentDetailSerializer(refreshed_comment, context={"request": request}).data,
            },
        )


class CommentHistoryView(PermissionEnforcerMixin, PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        comment = get_comment_for_user(comment_id=pk, user=request.user)
        if not comment:
            return success_response(
                request=request,
                message="Comment not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.enforce_permission(request=request, permission_class=IsTaskTeamMember, obj=comment)
        queryset = comment.versions.select_related("edited_by").order_by("-edited_at", "-created_at")
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=CommentVersionSerializer,
            message="Comment edit history retrieved successfully.",
        )
