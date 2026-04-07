from __future__ import annotations

from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from apps.common.api.mixins import PaginatedAPIViewMixin
from apps.common.responses import success_response
from apps.common.utils import coerce_bool_query_param
from apps.memberships.serializers import (
    InviteMemberSerializer,
    MembershipSerializer,
    TeamInvitationSerializer,
    UpdateInvitationRoleSerializer,
    UpdateMemberRoleSerializer,
)
from apps.memberships.selectors import get_team_invitations, get_team_invitation_by_id, get_team_member_by_id
from apps.memberships.services import (
    change_member_role,
    invite_member_to_team,
    remove_member_from_team,
    update_team_invitation_role,
)
from apps.teams.permissions import require_team_admin, require_team_inviter, require_team_member
from apps.teams.selectors import get_team_by_id_for_user, get_user_teams
from apps.teams.serializers import TeamCreateSerializer, TeamDetailSerializer, TeamListSerializer, TeamUpdateSerializer
from apps.teams.services import archive_team, create_team_with_owner, delete_team_if_allowed, update_team


class TeamListCreateView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=TeamListSerializer(many=True))
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        include_archived = coerce_bool_query_param(request.query_params.get("is_archived"))
        queryset = get_user_teams(user=request.user, include_archived=include_archived if include_archived is not None else False)
        if search := str(request.query_params.get("search", "")).strip():
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(slug__icontains=search)
            )
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=TeamListSerializer,
            message="Teams retrieved successfully.",
        )

    @extend_schema(request=TeamCreateSerializer, responses=TeamDetailSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = TeamCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = create_team_with_owner(
            created_by=request.user,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
            allow_manager_invites=serializer.validated_data.get("allow_manager_invites", False),
        )
        return success_response(
            request=request,
            message="Team created successfully.",
            data=TeamDetailSerializer(team, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
        )


class TeamDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_team(self, *, team_id, user, include_archived: bool | None = False):
        team = get_team_by_id_for_user(team_id=team_id, user=user, include_archived=include_archived)
        if not team:
            raise NotFound("Team not found.")
        return team

    @extend_schema(responses=TeamDetailSerializer)
    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        team = self.get_team(team_id=pk, user=request.user)
        require_team_member(team=team, user=request.user)
        return success_response(
            request=request,
            message="Team retrieved successfully.",
            data=TeamDetailSerializer(team, context={"request": request}).data,
        )

    @extend_schema(request=TeamUpdateSerializer, responses=TeamDetailSerializer)
    def patch(self, request, pk, *args, **kwargs):  # type: ignore[override]
        team = self.get_team(team_id=pk, user=request.user)
        require_team_admin(team=team, user=request.user)
        serializer = TeamUpdateSerializer(team, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_team = update_team(team=team, actor=request.user, **serializer.validated_data)
        return success_response(
            request=request,
            message="Team updated successfully.",
            data=TeamDetailSerializer(updated_team, context={"request": request}).data,
        )

    def delete(self, request, pk, *args, **kwargs):  # type: ignore[override]
        team = self.get_team(team_id=pk, user=request.user, include_archived=None)
        require_team_admin(team=team, user=request.user)
        delete_team_if_allowed(team=team, actor=request.user)
        return success_response(
            request=request,
            message="Team deleted successfully.",
            data=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )


class TeamArchiveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=TeamDetailSerializer)
    def post(self, request, pk, *args, **kwargs):  # type: ignore[override]
        team = get_team_by_id_for_user(team_id=pk, user=request.user, include_archived=None)
        if not team:
            raise NotFound("Team not found.")
        require_team_admin(team=team, user=request.user)
        archived_team = archive_team(team=team, actor=request.user)
        return success_response(
            request=request,
            message="Team archived successfully.",
            data=TeamDetailSerializer(archived_team, context={"request": request}).data,
        )


class TeamMemberListView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=MembershipSerializer(many=True))
    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        from apps.memberships.models import Membership

        team = get_team_by_id_for_user(team_id=pk, user=request.user)
        if not team:
            raise NotFound("Team not found.")
        require_team_member(team=team, user=request.user)

        queryset = (
            team.memberships.filter(status=Membership.Status.ACTIVE)
            .select_related("user", "team", "invited_by")
            .order_by("role", "user__name", "user__email")
        )
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=MembershipSerializer,
            message="Team members retrieved successfully.",
            serializer_context={},
        )


class TeamInvitationListCreateView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=TeamInvitationSerializer(many=True))
    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        team = get_team_by_id_for_user(team_id=pk, user=request.user)
        if not team:
            raise NotFound("Team not found.")
        require_team_inviter(team=team, user=request.user)

        queryset = get_team_invitations(team=team)
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=TeamInvitationSerializer,
            message="Pending invitations retrieved successfully.",
            serializer_context={},
        )

    @extend_schema(request=InviteMemberSerializer, responses=TeamInvitationSerializer)
    def post(self, request, pk, *args, **kwargs):  # type: ignore[override]
        team = get_team_by_id_for_user(team_id=pk, user=request.user)
        if not team:
            raise NotFound("Team not found.")
        require_team_inviter(team=team, user=request.user)

        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = invite_member_to_team(
            team=team,
            invited_by=request.user,
            email=serializer.validated_data["email"],
            role=serializer.validated_data["role"],
            custom_message=serializer.validated_data.get("custom_message", ""),
        )
        return success_response(
            request=request,
            message="Invitation sent successfully.",
            data=TeamInvitationSerializer(invitation).data,
            status_code=status.HTTP_201_CREATED,
        )


class TeamInvitationRoleUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=UpdateInvitationRoleSerializer, responses=TeamInvitationSerializer)
    def patch(self, request, pk, invitation_id, *args, **kwargs):  # type: ignore[override]
        team = get_team_by_id_for_user(team_id=pk, user=request.user)
        if not team:
            raise NotFound("Team not found.")
        require_team_inviter(team=team, user=request.user)

        invitation = get_team_invitation_by_id(team=team, invitation_id=invitation_id)
        if not invitation:
            raise NotFound("Invitation not found.")

        serializer = UpdateInvitationRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_invitation = update_team_invitation_role(
            invitation=invitation,
            actor=request.user,
            new_role=serializer.validated_data["role"],
        )
        return success_response(
            request=request,
            message="Invitation role updated successfully.",
            data=TeamInvitationSerializer(updated_invitation).data,
        )


class TeamMemberRoleUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=UpdateMemberRoleSerializer, responses=MembershipSerializer)
    def patch(self, request, pk, member_id, *args, **kwargs):  # type: ignore[override]
        team = get_team_by_id_for_user(team_id=pk, user=request.user)
        if not team:
            raise NotFound("Team not found.")
        require_team_admin(team=team, user=request.user)

        membership = get_team_member_by_id(team=team, membership_id=member_id)
        if not membership:
            raise NotFound("Membership not found.")

        serializer = UpdateMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_membership = change_member_role(
            team=team,
            actor=request.user,
            membership=membership,
            new_role=serializer.validated_data["role"],
        )
        return success_response(
            request=request,
            message="Member role updated successfully.",
            data=MembershipSerializer(updated_membership).data,
        )


class TeamMemberRemoveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, member_id, *args, **kwargs):  # type: ignore[override]
        team = get_team_by_id_for_user(team_id=pk, user=request.user)
        if not team:
            raise NotFound("Team not found.")
        require_team_admin(team=team, user=request.user)

        membership = get_team_member_by_id(team=team, membership_id=member_id)
        if not membership:
            raise NotFound("Membership not found.")

        remove_member_from_team(team=team, actor=request.user, membership=membership)
        return success_response(
            request=request,
            message="Member removed successfully.",
            data=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )
