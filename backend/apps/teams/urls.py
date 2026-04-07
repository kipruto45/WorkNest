from django.urls import path

from apps.teams.views import (
    TeamArchiveView,
    TeamDetailView,
    TeamInvitationListCreateView,
    TeamInvitationRoleUpdateView,
    TeamListCreateView,
    TeamMemberListView,
    TeamMemberRemoveView,
    TeamMemberRoleUpdateView,
)

app_name = "teams"

urlpatterns = [
    path("", TeamListCreateView.as_view(), name="list-create"),
    path("<uuid:pk>/", TeamDetailView.as_view(), name="detail"),
    path("<uuid:pk>/archive/", TeamArchiveView.as_view(), name="archive"),
    path("<uuid:pk>/members/", TeamMemberListView.as_view(), name="members"),
    path("<uuid:pk>/members/invite/", TeamInvitationListCreateView.as_view(), name="invite-member"),
    path("<uuid:pk>/invitations/", TeamInvitationListCreateView.as_view(), name="invitations"),
    path("<uuid:pk>/invitations/<uuid:invitation_id>/role/", TeamInvitationRoleUpdateView.as_view(), name="invitation-role"),
    path("<uuid:pk>/members/<uuid:member_id>/role/", TeamMemberRoleUpdateView.as_view(), name="member-role"),
    path("<uuid:pk>/members/<uuid:member_id>/", TeamMemberRemoveView.as_view(), name="member-remove"),
]
