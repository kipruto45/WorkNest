from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_comment_action
from rest_framework.exceptions import ValidationError

from apps.comments.constants import COMMENT_MAX_LENGTH, DELETED_COMMENT_PLACEHOLDER
from apps.comments.models import Comment, CommentReaction, CommentVersion
from apps.comments.parsers import resolve_mentions_for_team
from apps.realtime.constants import COMMENT_CREATED_EVENT, COMMENT_DELETED_EVENT, COMMENT_UPDATED_EVENT
from apps.realtime.services import send_comment_event


def _normalize_content(content: str) -> str:
    normalized = (content or "").strip()
    if not normalized:
        raise ValidationError({"content": ["This field may not be blank."]})
    if len(normalized) > COMMENT_MAX_LENGTH:
        raise ValidationError({"content": [f"Comment content cannot exceed {COMMENT_MAX_LENGTH} characters."]})
    return normalized


def validate_comment_parent(*, task, parent: Comment | None) -> Comment | None:
    if parent is None:
        return None
    if parent.task_id != task.id:
        raise ValidationError({"parent": ["Parent comment must belong to the same task."]})
    if parent.is_deleted:
        raise ValidationError({"parent": ["You cannot reply to a deleted comment."]})
    return parent


def extract_mentions_from_comment(*, content: str, team) -> list:
    return resolve_mentions_for_team(content=content, team=team)


@transaction.atomic
def create_comment(*, task, author, content: str, parent: Comment | None = None) -> tuple[Comment, list]:
    if task.is_archived:
        raise ValidationError({"task": ["Archived tasks cannot receive new comments."]})

    normalized_content = _normalize_content(content)
    validated_parent = validate_comment_parent(task=task, parent=parent)
    comment = Comment.objects.create(
        task=task,
        author=author,
        content=normalized_content,
        parent=validated_parent,
    )
    mentions = extract_mentions_from_comment(content=normalized_content, team=task.team)
    from apps.notifications.services import notify_comment_activity

    transaction.on_commit(lambda: notify_comment_activity(comment=comment, mentions=mentions))
    transaction.on_commit(lambda: send_comment_event(comment=comment, event_name=COMMENT_CREATED_EVENT))
    log_comment_action(
        actor=author,
        action=AuditAction.COMMENT_CREATED,
        comment=comment,
        metadata=build_audit_metadata(parent_id=comment.parent_id, mentioned_user_ids=[user.id for user in mentions]),
    )
    return comment, mentions


@transaction.atomic
def update_comment(*, comment: Comment, content: str, actor=None) -> tuple[Comment, list]:
    if comment.is_deleted:
        raise ValidationError({"comment": ["Deleted comments cannot be edited."]})

    normalized_content = _normalize_content(content)
    if normalized_content == comment.content:
        return comment, extract_mentions_from_comment(content=normalized_content, team=comment.task.team)

    CommentVersion.objects.create(
        comment=comment,
        content=comment.content,
        edited_by=actor or comment.author,
        edited_at=timezone.now(),
    )
    comment.content = normalized_content
    comment.is_edited = True
    comment.edited_at = timezone.now()
    comment.save(update_fields=["content", "is_edited", "edited_at", "updated_at"])
    mentions = extract_mentions_from_comment(content=normalized_content, team=comment.task.team)
    from apps.notifications.services import notify_comment_mentions

    transaction.on_commit(lambda: notify_comment_mentions(comment=comment, mentions=mentions))
    transaction.on_commit(lambda: send_comment_event(comment=comment, event_name=COMMENT_UPDATED_EVENT))
    log_comment_action(
        actor=actor or comment.author,
        action=AuditAction.COMMENT_UPDATED,
        comment=comment,
        metadata=build_audit_metadata(
            mentioned_user_ids=[user.id for user in mentions],
            is_edited=comment.is_edited,
            history_count=comment.versions.count(),
        ),
    )
    return comment, mentions


@transaction.atomic
def delete_comment(*, comment: Comment, actor=None) -> Comment:
    if comment.is_deleted:
        return comment

    comment.is_deleted = True
    comment.deleted_at = timezone.now()
    comment.content = DELETED_COMMENT_PLACEHOLDER
    comment.save(update_fields=["is_deleted", "deleted_at", "content", "updated_at"])
    log_comment_action(
        actor=actor,
        action=AuditAction.COMMENT_DELETED,
        comment=comment,
        metadata=build_audit_metadata(parent_id=comment.parent_id, task_title=comment.task.title),
    )
    transaction.on_commit(lambda: send_comment_event(comment=comment, event_name=COMMENT_DELETED_EVENT))
    return comment


@transaction.atomic
def reply_to_comment(*, parent_comment: Comment, author, content: str) -> tuple[Comment, list]:
    return create_comment(
        task=parent_comment.task,
        author=author,
        content=content,
        parent=parent_comment,
    )


@transaction.atomic
def toggle_comment_reaction(*, comment: Comment, user, emoji: str) -> tuple[bool, CommentReaction | None]:
    if comment.is_deleted:
        raise ValidationError({"comment": ["Deleted comments cannot receive reactions."]})

    existing = CommentReaction.objects.filter(comment=comment, user=user, emoji=emoji).first()
    if existing:
        existing.delete()
        transaction.on_commit(lambda: send_comment_event(comment=comment, event_name=COMMENT_UPDATED_EVENT))
        return False, None

    reaction = CommentReaction.objects.create(comment=comment, user=user, emoji=emoji)
    transaction.on_commit(lambda: send_comment_event(comment=comment, event_name=COMMENT_UPDATED_EVENT))
    return True, reaction
