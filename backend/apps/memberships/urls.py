from django.urls import path

from apps.memberships.views import (
    TeamInvitationAcceptView,
    TeamInvitationDeclineView,
    TeamInvitationDetailView,
    TeamInvitationResendView,
    TeamInvitationRevokeView,
)

app_name = "memberships"

urlpatterns = [
    path("<str:token>/", TeamInvitationDetailView.as_view(), name="detail"),
    path("<str:token>/accept/", TeamInvitationAcceptView.as_view(), name="accept"),
    path("<str:token>/decline/", TeamInvitationDeclineView.as_view(), name="decline"),
    path("<uuid:invitation_id>/resend/", TeamInvitationResendView.as_view(), name="resend"),
    path("<uuid:invitation_id>/revoke/", TeamInvitationRevokeView.as_view(), name="revoke"),
]
