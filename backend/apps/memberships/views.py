from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from apps.common.responses import success_response
from apps.memberships.selectors import get_invitation_by_token
from apps.memberships.serializers import MembershipSerializer, TeamInvitationDetailSerializer, TeamInvitationSerializer
from apps.memberships.services import (
    accept_team_invitation,
    decline_team_invitation,
    refresh_team_invitation_state,
    resend_team_invitation,
    revoke_team_invitation,
)
from apps.memberships.selectors import get_invitation_by_id


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
