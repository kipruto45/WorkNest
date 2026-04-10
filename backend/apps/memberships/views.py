from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from apps.common.responses import success_response
from apps.memberships.selectors import (
    get_invitation_by_id,
    get_invitation_by_token,
    get_team_invite_link_by_id,
    get_team_invite_link_by_token,
)
from apps.memberships.serializers import (
    MembershipSerializer,
    TeamInvitationDetailSerializer,
    TeamInvitationSerializer,
    TeamInviteLinkCreateSerializer,
    TeamInviteLinkResolveSerializer,
    TeamInviteLinkSerializer,
)
from apps.memberships.services import (
    accept_team_invitation,
    accept_team_invite_link,
    create_team_invite_link,
    decline_team_invitation,
    refresh_team_invitation_state,
    regenerate_team_invite_link,
    resend_team_invitation,
    revoke_team_invitation,
    revoke_team_invite_link,
    track_team_invite_link_copy,
)
from apps.teams.permissions import require_team_inviter


class TeamInvitationDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=TeamInvitationDetailSerializer)
    def get(self, request, token, *args, **kwargs):  # type: ignore[override]
        invitation = get_invitation_by_token(token=token)
        if not invitation:
            raise NotFound("Invitation not found.")
        invitation = refresh_team_invitation_state(invitation=invitation)

        invitation_data = TeamInvitationDetailSerializer(invitation).data
        viewer_email = request.user.email if request.user.is_authenticated else ""
        invitation_data["viewer_state"] = {
            "is_authenticated": request.user.is_authenticated,
            "email": viewer_email,
            "email_matches": bool(viewer_email) and viewer_email.lower() == invitation.email.lower(),
        }
        return success_response(
            request=request,
            message="Invitation retrieved successfully.",
            data=invitation_data,
        )


class TeamInvitationAcceptView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=MembershipSerializer)
    def post(self, request, token, *args, **kwargs):  # type: ignore[override]
        invitation = get_invitation_by_token(token=token)
        if not invitation:
            raise NotFound("Invitation not found.")
        membership = accept_team_invitation(invitation=invitation, user=request.user)
        return success_response(
            request=request,
            message="Invitation accepted successfully.",
            data=MembershipSerializer(membership).data,
        )


class TeamInvitationDeclineView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=TeamInvitationSerializer)
    def post(self, request, token, *args, **kwargs):  # type: ignore[override]
        invitation = get_invitation_by_token(token=token)
        if not invitation:
            raise NotFound("Invitation not found.")
        declined = decline_team_invitation(invitation=invitation, user=request.user)
        return success_response(
            request=request,
            message="Invitation declined successfully.",
            data=TeamInvitationSerializer(declined).data,
        )


class TeamInvitationResendView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=TeamInvitationSerializer)
    def post(self, request, invitation_id, *args, **kwargs):  # type: ignore[override]
        invitation = get_invitation_by_id(invitation_id=invitation_id)
        if not invitation:
            raise NotFound("Invitation not found.")
        resent = resend_team_invitation(invitation=invitation, actor=request.user)
        return success_response(
            request=request,
            message="Invitation resent successfully.",
            data=TeamInvitationSerializer(resent).data,
        )


class TeamInvitationRevokeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=TeamInvitationSerializer)
    def post(self, request, invitation_id, *args, **kwargs):  # type: ignore[override]
        invitation = get_invitation_by_id(invitation_id=invitation_id)
        if not invitation:
            raise NotFound("Invitation not found.")
        revoked = revoke_team_invitation(invitation=invitation, actor=request.user)
        return success_response(
            request=request,
            message="Invitation revoked successfully.",
            data=TeamInvitationSerializer(revoked).data,
        )


class TeamInviteLinkListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=TeamInviteLinkCreateSerializer, responses=TeamInviteLinkSerializer)
    def get(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        from apps.teams.models import Team

        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            raise NotFound("Team not found.")
        require_team_inviter(team=team, user=request.user)
        from apps.memberships.selectors import get_team_invite_links

        invite_links = get_team_invite_links(team=team)
        return success_response(
            request=request,
            message="Invite links retrieved successfully.",
            data=TeamInviteLinkSerializer(invite_links, many=True).data,
        )

    @extend_schema(request=TeamInviteLinkCreateSerializer, responses=TeamInviteLinkSerializer)
    def post(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        from apps.teams.models import Team

        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            raise NotFound("Team not found.")
        require_team_inviter(team=team, user=request.user)

        serializer = TeamInviteLinkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invite_link = create_team_invite_link(
            team=team,
            actor=request.user,
            role=serializer.validated_data.get("role", "member"),
            label=serializer.validated_data.get("label", ""),
            expires_at=serializer.validated_data.get("expires_at"),
            max_uses=serializer.validated_data.get("max_uses"),
        )
        return success_response(
            request=request,
            message="Invite link created successfully.",
            data=TeamInviteLinkSerializer(invite_link).data,
        )


class TeamInviteLinkRevokeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=TeamInviteLinkSerializer)
    def post(self, request, team_id, invite_link_id, *args, **kwargs):  # type: ignore[override]
        from apps.teams.models import Team

        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            raise NotFound("Team not found.")
        require_team_inviter(team=team, user=request.user)

        invite_link = get_team_invite_link_by_id(team=team, invite_link_id=invite_link_id)
        if not invite_link:
            raise NotFound("Invite link not found.")

        revoked = revoke_team_invite_link(invite_link=invite_link, actor=request.user)
        return success_response(
            request=request,
            message="Invite link revoked successfully.",
            data=TeamInviteLinkSerializer(revoked).data,
        )


class TeamInviteLinkRegenerateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=TeamInviteLinkSerializer)
    def post(self, request, team_id, invite_link_id, *args, **kwargs):  # type: ignore[override]
        from apps.teams.models import Team

        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            raise NotFound("Team not found.")
        require_team_inviter(team=team, user=request.user)

        invite_link = get_team_invite_link_by_id(team=team, invite_link_id=invite_link_id)
        if not invite_link:
            raise NotFound("Invite link not found.")

        regenerated = regenerate_team_invite_link(invite_link=invite_link, actor=request.user)
        return success_response(
            request=request,
            message="Invite link regenerated successfully.",
            data=TeamInviteLinkSerializer(regenerated).data,
        )


class TeamInviteLinkCopyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=TeamInviteLinkSerializer)
    def post(self, request, team_id, invite_link_id, *args, **kwargs):  # type: ignore[override]
        from apps.teams.models import Team

        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            raise NotFound("Team not found.")
        require_team_inviter(team=team, user=request.user)

        invite_link = get_team_invite_link_by_id(team=team, invite_link_id=invite_link_id)
        if not invite_link:
            raise NotFound("Invite link not found.")

        tracked = track_team_invite_link_copy(invite_link=invite_link, actor=request.user)
        return success_response(
            request=request,
            message="Invite link copied.",
            data=TeamInviteLinkSerializer(tracked).data,
        )


class TeamInviteLinkResolveView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=TeamInviteLinkResolveSerializer)
    def get(self, request, token, *args, **kwargs):  # type: ignore[override]
        invite_link = get_team_invite_link_by_token(token=token)
        if not invite_link:
            raise NotFound("Invite link not found.")

        invite_link_data = TeamInviteLinkResolveSerializer(invite_link).data
        viewer_email = request.user.email if request.user.is_authenticated else ""
        viewer_membership = None
        if request.user.is_authenticated:
            from apps.memberships.selectors import get_team_member
            from apps.memberships.models import Membership

            viewer_membership = get_team_member(team=invite_link.team, user=request.user)

        invite_link_data["viewer_state"] = {
            "is_authenticated": request.user.is_authenticated,
            "email": viewer_email,
            "is_already_member": bool(viewer_membership and viewer_membership.status == Membership.Status.ACTIVE),
            "membership_role": viewer_membership.role if viewer_membership else None,
        }
        return success_response(
            request=request,
            message="Invite link resolved successfully.",
            data=invite_link_data,
        )


class TeamInviteLinkAcceptView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=MembershipSerializer)
    def post(self, request, token, *args, **kwargs):  # type: ignore[override]
        invite_link = get_team_invite_link_by_token(token=token)
        if not invite_link:
            raise NotFound("Invite link not found.")

        membership = accept_team_invite_link(invite_link=invite_link, user=request.user)
        return success_response(
            request=request,
            message="Joined team successfully.",
            data=MembershipSerializer(membership).data,
        )
