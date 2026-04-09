from __future__ import annotations

from django.db.models import Prefetch, Q

from django.contrib.auth import get_user_model

from apps.memberships.models import Membership

User = get_user_model()


def get_current_user_profile(*, user):
    return User.objects.get(pk=user.pk)


def get_user_by_email(*, email: str):
    if not email:
        return None
    return User.objects.filter(email__iexact=email).first()


def get_user_by_phone(*, phone_number: str):
    if not phone_number:
        return None
    return User.objects.filter(phone_number=phone_number).first()


def get_admin_user_queryset():
    return User.objects.prefetch_related(
        Prefetch(
            "team_memberships",
            queryset=Membership.objects.select_related("team").filter(status=Membership.Status.ACTIVE),
        )
    ).order_by("name", "email")


def filter_admin_users(*, query: str = "", is_active=None, account_type: str = "", team_id: str = ""):
    queryset = get_admin_user_queryset()
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    if account_type:
        queryset = queryset.filter(account_type=account_type)
    if team_id:
        queryset = queryset.filter(team_memberships__team_id=team_id, team_memberships__status=Membership.Status.ACTIVE)
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone_number__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
    return queryset.distinct()
