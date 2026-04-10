from django.urls import path

from apps.memberships.views import (
    TeamInviteLinkAcceptView,
    TeamInviteLinkCopyView,
    TeamInviteLinkListCreateView,
    TeamInviteLinkRegenerateView,
    TeamInviteLinkResolveView,
    TeamInviteLinkRevokeView,
)

app_name = "invite_links"

urlpatterns = [
    path("<uuid:team_id>/invite-links/", TeamInviteLinkListCreateView.as_view(), name="list-create"),
    path("<uuid:team_id>/invite-links/<uuid:invite_link_id>/revoke/", TeamInviteLinkRevokeView.as_view(), name="revoke"),
    path("<uuid:team_id>/invite-links/<uuid:invite_link_id>/regenerate/", TeamInviteLinkRegenerateView.as_view(), name="regenerate"),
    path("<uuid:team_id>/invite-links/<uuid:invite_link_id>/copy/", TeamInviteLinkCopyView.as_view(), name="copy"),
    path("resolve/<str:token>/", TeamInviteLinkResolveView.as_view(), name="resolve"),
    path("accept/<str:token>/", TeamInviteLinkAcceptView.as_view(), name="accept"),
]