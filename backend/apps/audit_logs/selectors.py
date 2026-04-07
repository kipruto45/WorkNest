from __future__ import annotations

from django.db.models import QuerySet

from apps.audit_logs.models import AuditLog


def _base_audit_log_queryset() -> QuerySet[AuditLog]:
    return AuditLog.objects.select_related("actor", "team")


def get_audit_log_by_id(*, log_id) -> AuditLog | None:
    return _base_audit_log_queryset().filter(pk=log_id).first()


def get_team_audit_logs(*, team) -> QuerySet[AuditLog]:
    return _base_audit_log_queryset().filter(team=team)


def get_actor_audit_logs(*, user) -> QuerySet[AuditLog]:
    return _base_audit_log_queryset().filter(actor=user)


def get_target_audit_logs(*, target_type: str, target_id: str) -> QuerySet[AuditLog]:
    return _base_audit_log_queryset().filter(target_type=target_type, target_id=str(target_id))


def filter_audit_logs(queryset: QuerySet[AuditLog], filters: dict) -> QuerySet[AuditLog]:
    if actor := filters.get("actor"):
        queryset = queryset.filter(actor_id=actor)
    if action := filters.get("action"):
        queryset = queryset.filter(action=action)
    if team := filters.get("team"):
        queryset = queryset.filter(team_id=team)
    if target_type := filters.get("target_type"):
        queryset = queryset.filter(target_type=target_type)
    if target_id := filters.get("target_id"):
        queryset = queryset.filter(target_id=str(target_id))
    if date_from := filters.get("date_from"):
        queryset = queryset.filter(created_at__gte=date_from)
    if date_to := filters.get("date_to"):
        queryset = queryset.filter(created_at__lte=date_to)
    return queryset.order_by("-created_at")
