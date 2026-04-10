from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from apps.audit_logs.constants import AUDIT_REDACTED_VALUE, AUDIT_SENSITIVE_METADATA_KEYS, AuditAction
from apps.audit_logs.middleware import get_current_audit_request_context
from apps.audit_logs.models import AuditLog

MODEL_NAME_ALIASES = {
    "teaminvitation": "team_invitation",
    "loginactivity": "login_activity",
}


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().strip()
    return any(sensitive in normalized for sensitive in AUDIT_SENSITIVE_METADATA_KEYS)


def _normalize_value(value):
    if isinstance(value, dict):
        return {
            str(key): AUDIT_REDACTED_VALUE if _is_sensitive_key(str(key)) else _normalize_value(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, (list, tuple, set)):
        return [_normalize_value(item) for item in value if item is not None]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "pk"):
        return str(value.pk)
    return str(value)


def build_audit_metadata(**kwargs) -> dict:
    return _normalize_value({key: value for key, value in kwargs.items() if value is not None}) or {}


def serialize_target_for_audit(*, target=None, target_type: str = "", target_id: str = "", target_repr: str = "") -> dict:
    if target is None:
        return {
            "target_type": target_type,
            "target_id": str(target_id) if target_id else "",
            "target_repr": target_repr[:255] if target_repr else "",
        }

    resolved_target_type = target_type or MODEL_NAME_ALIASES.get(target._meta.model_name, target._meta.model_name)
    resolved_target_id = str(target_id or getattr(target, "pk", "") or "")
    resolved_target_repr = target_repr or getattr(target, "title", "") or getattr(target, "name", "") or getattr(
        target, "email", ""
    )
    if not resolved_target_repr:
        resolved_target_repr = str(target)

    return {
        "target_type": resolved_target_type[:64],
        "target_id": resolved_target_id[:64],
        "target_repr": str(resolved_target_repr)[:255],
    }


def infer_audit_team(*, target=None, team=None):
    if team is not None:
        return team
    if target is None:
        return None
    if getattr(target, "team", None) is not None:
        return target.team
    if getattr(target, "task", None) is not None and getattr(target.task, "team", None) is not None:
        return target.task.team
    return None


def create_audit_log(
    *,
    actor=None,
    action: str,
    target=None,
    target_type: str = "",
    target_id: str = "",
    target_repr: str = "",
    team=None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    user_agent: str = "",
) -> AuditLog:
    valid_actions = {choice[0] for choice in AuditAction.choices}
    if action not in valid_actions:
        raise ValueError(f"Unsupported audit action: {action}")

    request_context = get_current_audit_request_context()
    serialized_target = serialize_target_for_audit(
        target=target,
        target_type=target_type,
        target_id=target_id,
        target_repr=target_repr,
    )

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        team=infer_audit_team(target=target, team=team),
        metadata=build_audit_metadata(**(metadata or {})),
        ip_address=ip_address or request_context.get("ip_address"),
        user_agent=(user_agent or request_context.get("user_agent") or "")[:1000],
        **serialized_target,
    )


def log_auth_action(*, actor=None, action: str, target=None, metadata: dict | None = None, target_repr: str = "") -> AuditLog:
    return create_audit_log(
        actor=actor,
        action=action,
        target=target,
        target_type="user" if actor or target else "auth",
        target_repr=target_repr,
        metadata=metadata,
    )


def log_team_action(*, actor, action: str, team, metadata: dict | None = None, target=None) -> AuditLog:
    return create_audit_log(
        actor=actor,
        action=action,
        target=target or team,
        team=team,
        metadata=metadata,
    )


def log_membership_action(
    *,
    actor,
    action: str,
    membership=None,
    invitation=None,
    team=None,
    target=None,
    metadata: dict | None = None,
) -> AuditLog:
    target = target or membership or invitation
    return create_audit_log(
        actor=actor,
        action=action,
        target=target,
        team=team or infer_audit_team(target=target),
        metadata=metadata,
    )


def log_task_action(*, actor, action: str, task, metadata: dict | None = None) -> AuditLog:
    return create_audit_log(actor=actor, action=action, target=task, team=task.team, metadata=metadata)


def log_comment_action(*, actor, action: str, comment, metadata: dict | None = None) -> AuditLog:
    return create_audit_log(actor=actor, action=action, target=comment, team=comment.task.team, metadata=metadata)


def log_attachment_action(*, actor, action: str, attachment, metadata: dict | None = None) -> AuditLog:
    return create_audit_log(actor=actor, action=action, target=attachment, team=attachment.task.team, metadata=metadata)


def log_notification_action(
    *,
    actor,
    action: str,
    notification=None,
    metadata: dict | None = None,
    target_repr: str = "",
    target_type: str = "notification",
) -> AuditLog:
    return create_audit_log(
        actor=actor,
        action=action,
        target=notification,
        target_type=target_type if notification is None else "",
        team=getattr(notification, "team", None),
        metadata=metadata,
        target_repr=target_repr,
    )
