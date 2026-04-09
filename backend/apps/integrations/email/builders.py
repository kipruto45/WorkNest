from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.utils import timezone
from django.utils.text import Truncator

from apps.integrations.email.base import QueuedEmailPayload
from apps.notifications.constants import NotificationType

EMAIL_TYPE_PASSWORD_RESET = "password_reset"
EMAIL_TYPE_TEAM_INVITE = "team_invite"
EMAIL_TYPE_INVITATION_REMINDER = "invitation_reminder"
EMAIL_TYPE_INVITATION_REVOKED = "invitation_revoked"
EMAIL_TYPE_TASK_ASSIGNED = "task_assigned"
EMAIL_TYPE_DEADLINE_APPROACHING = "deadline_approaching"
EMAIL_TYPE_COMMENT_POSTED = "comment_posted"
EMAIL_TYPE_MENTIONED_IN_COMMENT = "mentioned_in_comment"
EMAIL_TYPE_WELCOME = "welcome"
EMAIL_TYPE_EMAIL_VERIFICATION = "email_verification"
EMAIL_TYPE_CREDENTIAL_CHANGE = "credential_change_verification"
EMAIL_TYPE_INVITATION_ACCEPTED = "invitation_accepted"
EMAIL_TYPE_ROLE_CHANGED = "role_changed"
EMAIL_TYPE_TASK_STATUS_CHANGED = "task_status_changed"
EMAIL_TYPE_ATTACHMENT_UPLOADED = "attachment_uploaded"
EMAIL_TYPE_NOTIFICATION = "notification"
EMAIL_TYPE_ADMIN_COMMUNICATION = "admin_communication"
DEFAULT_PUBLIC_WEBAPP_URL = "https://work-nest-lemon.vercel.app"


def _get_app_name() -> str:
    return getattr(settings, "APP_NAME", "WorkNest")


def _get_support_email() -> str:
    return getattr(settings, "SUPPORT_EMAIL", getattr(settings, "DEFAULT_FROM_EMAIL", "support@example.com"))


def _get_admin_sender_email() -> str:
    return str(getattr(settings, "ADMIN_EMAIL", "") or getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()


def _is_local_hostname(hostname: str | None) -> bool:
    normalized = (hostname or "").strip().lower()
    return normalized in {"", "localhost", "127.0.0.1", "0.0.0.0"} or normalized.endswith(".local")


def _is_public_absolute_url(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    return bool(parsed.scheme and parsed.netloc and not _is_local_hostname(parsed.hostname))


def _origin_from_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _strip_known_frontend_suffix(url: str) -> str:
    cleaned = _origin_from_url(url)
    for suffix in ("/invitations", "/reset-password", "/logo_hd.png"):
        if cleaned.endswith(suffix):
            return cleaned[: -len(suffix)]
    return cleaned


def _get_frontend_url() -> str:
    public_webapp_url = str(getattr(settings, "PUBLIC_WEBAPP_URL", "")).strip().rstrip("/")
    if _is_public_absolute_url(public_webapp_url):
        return public_webapp_url

    configured_frontend = str(getattr(settings, "FRONTEND_URL", "")).strip().rstrip("/")
    if _is_public_absolute_url(configured_frontend):
        return configured_frontend

    for candidate in (
        getattr(settings, "INVITE_LINK_BASE_URL", ""),
        getattr(settings, "PASSWORD_RESET_LINK_BASE_URL", ""),
        getattr(settings, "LOGO_URL", ""),
    ):
        candidate_base = _strip_known_frontend_suffix(str(candidate))
        if _is_public_absolute_url(candidate_base):
            return candidate_base.rstrip("/")

    if str(getattr(settings, "ENVIRONMENT", "")).strip().lower() == "production":
        return DEFAULT_PUBLIC_WEBAPP_URL

    return configured_frontend


def _get_brand_mark() -> str:
    words = [word[:1] for word in _get_app_name().replace("-", " ").split() if word]
    if not words:
        return "WN"
    return "".join(words[:2]).upper()


def _get_logo_url() -> str:
    configured_logo_url = str(getattr(settings, "LOGO_URL", "")).strip()
    if _is_public_absolute_url(configured_logo_url):
        return configured_logo_url
    frontend_url = _get_frontend_url()
    if frontend_url:
        return f"{frontend_url}/logo_hd.png"
    return ""


def _frontend_path(path: str) -> str:
    frontend_url = _get_frontend_url()
    if not frontend_url:
        return path
    return f"{frontend_url}{path}"


def _display_name(user, fallback: str = "A teammate") -> str:
    if user is None:
        return fallback
    if getattr(user, "name", ""):
        return user.name
    if getattr(user, "first_name", ""):
        return user.first_name
    if getattr(user, "email", ""):
        return user.email.split("@", 1)[0]
    return fallback


def _shorten_text(value: str, *, limit: int = 180) -> str:
    return Truncator((value or "").strip()).chars(limit)


def _format_datetime(value) -> str:
    if not value:
        return "Not set"
    return timezone.localtime(value).strftime("%B %d, %Y at %I:%M %p")


def _format_date(value) -> str:
    if not value:
        return "Not set"
    return timezone.localtime(value).strftime("%B %d, %Y")


def _task_url(*, task, comment=None) -> str:
    path = f"/tasks/{task.id}"
    if comment is not None:
        path = f"{path}?comment={comment.id}"
    return _frontend_path(path)


def _team_url(*, team) -> str:
    return _frontend_path(f"/teams/{team.id}/overview")


def _invitation_url(*, token: str) -> str:
    base_url = getattr(settings, "INVITE_LINK_BASE_URL", "").rstrip("/")
    if _is_public_absolute_url(base_url):
        return f"{base_url}/{token}"
    return _frontend_path(f"/invitations/{token}")


def _dashboard_url() -> str:
    return _frontend_path("/dashboard")


def _safe_cta_link(link: str) -> str:
    link = (link or "").strip()
    if not link:
        return ""
    if _is_public_absolute_url(link):
        return link
    return _frontend_path(link)


def _base_context(**overrides) -> dict[str, Any]:
    context = {
        "app_name": _get_app_name(),
        "brand_mark": _get_brand_mark(),
        "support_email": _get_support_email(),
        "logo_url": _get_logo_url(),
        "reason_text": f"You received this email because of activity in {_get_app_name()}.",
        "eyebrow": "Workspace update",
        "preheader_text": "",
        "button_text": "Open",
        "button_url": "",
        "decline_url": "",
        "button_hint": "",
        "detail_title": "Details",
        "detail_items": [],
        "preview_label": "",
        "preview_text": "",
        "warning_text": "",
        "footer_note": "",
        "help_text": "",
        "greeting": "Hello,",
        "title": "",
        "intro": "",
        "accent_color": "#047857",
        "accent_soft": "#ecfdf5",
        "accent_border": "#a7f3d0",
        "accent_text": "#065f46",
    }
    context.update(overrides)
    return context


def _build_job(
    *,
    email_type: str,
    template_name: str,
    recipient_email: str,
    subject: str,
    context: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    dedupe_key: str = "",
    source: str = "",
    related_object_type: str = "",
    related_object_id: str = "",
    provider_metadata: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    from_email: str | None = None,
) -> QueuedEmailPayload:
    return QueuedEmailPayload(
        email_type=email_type,
        template_name=template_name,
        recipient_email=recipient_email,
        subject=subject,
        context=context,
        metadata=metadata or {},
        from_email=from_email,
        dedupe_key=dedupe_key,
        source=source,
        related_object_type=related_object_type,
        related_object_id=related_object_id,
        provider_metadata=provider_metadata or {},
        headers=headers or {},
    )


def build_admin_communication_email_payload(*, communication, recipient, actor=None) -> QueuedEmailPayload:
    sender_name = _display_name(actor, "WorkNest Admin")
    button_text = communication.cta_label.strip() if communication.cta_label else "Open Workspace"
    button_url = _safe_cta_link(communication.cta_link) or _dashboard_url()
    context = _base_context(
        eyebrow="Admin communication",
        title=communication.title,
        greeting=f"Hello {_display_name(recipient, 'there')},",
        intro=communication.message,
        preheader_text=_shorten_text(communication.message, limit=120),
        button_text=button_text,
        button_url=button_url,
        button_hint="You can review this update in your workspace.",
        reason_text=f"You received this email from {sender_name} in {_get_app_name()}.",
        accent_color="#0f766e",
        accent_soft="#f0fdfa",
        accent_border="#99f6e4",
        accent_text="#0f766e",
    )
    return _build_job(
        email_type=EMAIL_TYPE_ADMIN_COMMUNICATION,
        template_name="admin_communication",
        recipient_email=recipient.email,
        subject=communication.title,
        context=context,
        metadata={
            "communication_id": str(communication.id),
            "audience_type": communication.audience_type,
            "channel_type": communication.channel_type,
            "cta_label": communication.cta_label,
            "cta_link": communication.cta_link,
        },
        dedupe_key=f"admin-communication:{communication.id}:{recipient.id}",
        source="admin_communication",
        related_object_type="admin_communication",
        related_object_id=str(communication.id),
    )


def build_password_reset_email_payload(*, user, reset_url: str, expires_in_minutes: int = 30) -> QueuedEmailPayload:
    context = _base_context(
        eyebrow="Security",
        title="Reset your password",
        greeting=f"Hi {_display_name(user, 'there')},",
        intro="We received a request to reset your password. Use the secure link below to choose a new one.",
        preheader_text="Use the secure link in this email to reset your password.",
        button_text="Reset Password",
        button_url=reset_url,
        button_hint="If the button does not open, copy and paste the link below into your browser.",
        detail_title="Security details",
        detail_items=[
            {"label": "Requested for", "value": user.email},
            {"label": "Link expires in", "value": f"{expires_in_minutes} minutes"},
        ],
        warning_text=f"This link expires in {expires_in_minutes} minutes.",
        help_text="If you did not request this, you can ignore this email and your password will stay unchanged.",
        footer_note="For security, never share password reset links with anyone.",
        reason_text=f"You received this email because a password reset was requested for your {_get_app_name()} account.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_PASSWORD_RESET,
        template_name="password_reset",
        recipient_email=user.email,
        subject="Reset your password",
        context=context,
        metadata={"user_id": str(user.id)},
        source="authentication.password_reset",
        related_object_type="user",
        related_object_id=str(user.id),
        provider_metadata={"categories": [EMAIL_TYPE_PASSWORD_RESET]},
    )


def build_email_verification_email_payload(*, user, verification_url: str) -> QueuedEmailPayload:
    context = _base_context(
        eyebrow="Verify your email",
        title="Confirm your email address",
        greeting=f"Hi {_display_name(user, 'there')},",
        intro="Confirm your email address to secure your account and enable trusted workspace notifications.",
        preheader_text="Confirm your email address to finish setting up your account.",
        button_text="Verify Email",
        button_url=verification_url,
        button_hint="If the button does not open, use the verification link below.",
        detail_title="Verification details",
        detail_items=[
            {"label": "Account", "value": user.email},
            {"label": "Status", "value": "Verification pending"},
        ],
        footer_note="For your safety, this verification link expires automatically.",
        help_text="If you did not create this account, you can ignore this email.",
        reason_text=f"You received this email because an account was created for this address in {_get_app_name()}.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_EMAIL_VERIFICATION,
        template_name="email_verification",
        recipient_email=user.email,
        subject="Verify your email address",
        context=context,
        from_email=_get_admin_sender_email(),
        metadata={"user_id": str(user.id)},
        dedupe_key=f"email-verification:{user.id}",
        source="authentication.email_verification",
        related_object_type="user",
        related_object_id=str(user.id),
        provider_metadata={"categories": [EMAIL_TYPE_EMAIL_VERIFICATION]},
    )


def build_credential_change_email_payload(*, user, new_email: str, code: str) -> QueuedEmailPayload:
    settings_url = _frontend_path("/settings")
    context = _base_context(
        eyebrow="Security",
        title="Confirm your new email address",
        greeting=f"Hi {_display_name(user, 'there')},",
        intro="Use the verification code below to confirm your new sign-in email address before the change is applied.",
        preheader_text="Verify your new email address with this code.",
        button_text="Open settings",
        button_url=settings_url,
        button_hint="If you're already in the app, enter the code from this email in the account settings screen.",
        detail_title="Verification details",
        detail_items=[
            {"label": "New email", "value": new_email},
            {"label": "Verification code", "value": code},
            {"label": "Expires in", "value": "10 minutes"},
        ],
        preview_label="Verification code",
        preview_text=code,
        footer_note="This code can only be used once.",
        help_text="If you did not request this change, ignore this email and keep using your current sign-in details.",
        reason_text=f"You received this email because a sign-in email change was requested for your {_get_app_name()} account.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_CREDENTIAL_CHANGE,
        template_name="email_verification",
        recipient_email=new_email,
        subject="Confirm your new email address",
        context=context,
        from_email=_get_admin_sender_email(),
        metadata={"user_id": str(user.id), "new_email": new_email},
        source="authentication.credential_change_email",
        related_object_type="user",
        related_object_id=str(user.id),
        provider_metadata={"categories": [EMAIL_TYPE_CREDENTIAL_CHANGE]},
    )


def build_team_invite_email_payload(*, invitation) -> QueuedEmailPayload:
    inviter_name = _display_name(invitation.invited_by)
    expiry_date = _format_date(invitation.expires_at)
    invitation_url = _invitation_url(token=invitation.token)
    context = _base_context(
        eyebrow="Team invitation",
        title="You're invited to join a team",
        intro=f"{inviter_name} invited you to join {invitation.team.name} as a {invitation.get_role_display().lower()}.",
        preheader_text=f"{inviter_name} invited you to join {invitation.team.name}.",
        button_text="Accept Invitation",
        button_url=invitation_url,
        decline_url=invitation_url,
        button_hint="Open the invitation to sign in, create an account, or respond.",
        detail_title="Invitation details",
        detail_items=[
            {"label": "Team", "value": invitation.team.name},
            {"label": "Role", "value": invitation.get_role_display()},
            {"label": "Invited by", "value": inviter_name},
            {"label": "Expires", "value": expiry_date},
        ],
        expiry_date=expiry_date,
        preview_label="Message from your teammate" if invitation.custom_message else "",
        preview_text=invitation.custom_message,
        footer_note="This invitation is reserved for the email address that received it.",
        help_text="You can create your account after opening the invitation if you do not already have one.",
        reason_text=f"You received this email because this address was invited to join a team in {_get_app_name()}.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_TEAM_INVITE,
        template_name="team_invitation",
        recipient_email=invitation.email,
        subject=f"You've been invited to join {invitation.team.name}",
        context=context,
        metadata={"team_id": str(invitation.team_id), "invitation_id": str(invitation.id), "role": invitation.role},
        dedupe_key=f"team-invite:{invitation.id}:{invitation.updated_at.isoformat()}",
        source="memberships.invitation",
        related_object_type="team_invitation",
        related_object_id=str(invitation.id),
        provider_metadata={"categories": [EMAIL_TYPE_TEAM_INVITE]},
    )


def build_invitation_reminder_email_payload(*, invitation) -> QueuedEmailPayload:
    inviter_name = _display_name(invitation.invited_by)
    expiry_date = _format_date(invitation.expires_at)
    context = _base_context(
        eyebrow="Invitation reminder",
        title="Your team invitation is still waiting",
        intro=f"{inviter_name} is still waiting for you to join {invitation.team.name}.",
        preheader_text=f"Your invitation to join {invitation.team.name} is still active.",
        button_text="Review Invitation",
        button_url=_invitation_url(token=invitation.token),
        button_hint="Open the invitation to accept it, decline it, or create an account.",
        detail_title="Invitation details",
        detail_items=[
            {"label": "Team", "value": invitation.team.name},
            {"label": "Role", "value": invitation.get_role_display()},
            {"label": "Expires", "value": expiry_date},
        ],
        expiry_date=expiry_date,
        preview_label="Message from your teammate" if invitation.custom_message else "",
        preview_text=invitation.custom_message,
        footer_note="This reminder helps you respond before the invitation expires.",
        reason_text=f"You received this email because your invitation to {invitation.team.name} is still pending.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_INVITATION_REMINDER,
        template_name="invitation_reminder",
        recipient_email=invitation.email,
        subject=f"Reminder: join {invitation.team.name}",
        context=context,
        metadata={"team_id": str(invitation.team_id), "invitation_id": str(invitation.id), "role": invitation.role},
        dedupe_key=f"team-invite-reminder:{invitation.id}",
        source="memberships.invitation",
        related_object_type="team_invitation",
        related_object_id=str(invitation.id),
        provider_metadata={"categories": [EMAIL_TYPE_INVITATION_REMINDER]},
    )


def build_invitation_revoked_email_payload(*, invitation, actor=None) -> QueuedEmailPayload:
    context = _base_context(
        eyebrow="Invitation update",
        title="This invitation has been revoked",
        intro=f"{_display_name(actor or invitation.invited_by)} revoked the invitation to join {invitation.team.name}.",
        preheader_text=f"The invitation to join {invitation.team.name} is no longer active.",
        button_text="View Invitation Status",
        button_url=_invitation_url(token=invitation.token),
        detail_title="Invitation details",
        detail_items=[
            {"label": "Team", "value": invitation.team.name},
            {"label": "Updated by", "value": _display_name(actor or invitation.invited_by)},
        ],
        help_text="If you still need access, ask a team admin to send a fresh invitation.",
        footer_note="The previous invitation link is no longer active.",
        warning_text="Any previous invitation link for this team has been disabled.",
        reason_text=f"You received this email because an invitation linked to this address was updated in {_get_app_name()}.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_INVITATION_REVOKED,
        template_name="invitation_revoked",
        recipient_email=invitation.email,
        subject=f"Invitation revoked for {invitation.team.name}",
        context=context,
        metadata={"team_id": str(invitation.team_id), "invitation_id": str(invitation.id)},
        dedupe_key=f"team-invite-revoked:{invitation.id}:{invitation.updated_at.isoformat()}",
        source="memberships.invitation",
        related_object_type="team_invitation",
        related_object_id=str(invitation.id),
        provider_metadata={"categories": [EMAIL_TYPE_INVITATION_REVOKED]},
    )


def build_task_assigned_email_payload(*, task, assigner, assignee) -> QueuedEmailPayload:
    context = _base_context(
        eyebrow="Task assignment",
        title="A task was assigned to you",
        greeting=f"Hi {_display_name(assignee, 'there')},",
        intro=f"{_display_name(assigner)} assigned you a task in {task.team.name}.",
        preheader_text=f"{task.title} was assigned to you in {task.team.name}.",
        button_text="Open Task",
        button_url=_task_url(task=task),
        detail_title="Task details",
        detail_items=[
            {"label": "Task", "value": task.title},
            {"label": "Team", "value": task.team.name},
            {"label": "Priority", "value": task.get_priority_display()},
            {"label": "Status", "value": task.get_status_display()},
            {"label": "Due date", "value": _format_datetime(task.due_date) if task.due_date else "No due date"},
        ],
        preview_label="Task summary" if task.description else "",
        preview_text=_shorten_text(task.description) if task.description else "",
        footer_note="Open the task to review details, update status, or coordinate with your team.",
        reason_text=f"You received this email because work was assigned to you in {_get_app_name()}.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_TASK_ASSIGNED,
        template_name="task_assigned",
        recipient_email=assignee.email,
        subject=f"New task assigned: {task.title}",
        context=context,
        metadata={"task_id": str(task.id), "team_id": str(task.team_id), "assignee_id": str(assignee.id)},
        dedupe_key=f"task-assigned:{task.id}:{assignee.id}:{task.updated_at.isoformat()}",
        source="tasks.assignment",
        related_object_type="task",
        related_object_id=str(task.id),
        provider_metadata={"categories": [EMAIL_TYPE_TASK_ASSIGNED]},
    )


def build_deadline_approaching_email_payload(*, task, recipient, reminder_window_hours: int) -> QueuedEmailPayload:
    context = _base_context(
        eyebrow="Deadline reminder",
        title="Task deadline approaching",
        greeting=f"Hi {_display_name(recipient, 'there')},",
        intro=f"{task.title} is due on {_format_datetime(task.due_date)}. This is your {reminder_window_hours}-hour reminder to review the task and update progress.",
        preheader_text=f"{task.title} is due soon. Review the latest status and due date.",
        button_text="Review Task",
        button_url=_task_url(task=task),
        detail_title="Deadline details",
        detail_items=[
            {"label": "Task", "value": task.title},
            {"label": "Team", "value": task.team.name},
            {"label": "Due", "value": _format_datetime(task.due_date)},
            {"label": "Status", "value": task.get_status_display()},
            {"label": "Priority", "value": task.get_priority_display()},
        ],
        warning_text="Update the task status if the timeline has changed.",
        footer_note="Deadline reminders are sent to help the team stay ahead of risk.",
        reason_text=f"You received this email because a task deadline is approaching in {_get_app_name()}.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_DEADLINE_APPROACHING,
        template_name="deadline_approaching",
        recipient_email=recipient.email,
        subject=f"Deadline approaching: {task.title}",
        context=context,
        metadata={"task_id": str(task.id), "team_id": str(task.team_id), "reminder_window_hours": reminder_window_hours},
        dedupe_key=f"deadline-reminder:{task.id}:{recipient.id}:{reminder_window_hours}",
        source="notifications.deadline",
        related_object_type="task",
        related_object_id=str(task.id),
        provider_metadata={"categories": [EMAIL_TYPE_DEADLINE_APPROACHING]},
    )


def build_comment_posted_email_payload(*, comment, task, recipient) -> QueuedEmailPayload:
    context = _base_context(
        eyebrow="Discussion update",
        title="New comment on a task",
        greeting=f"Hi {_display_name(recipient, 'there')},",
        intro=f"{_display_name(comment.author)} commented on {task.title}.",
        preheader_text=f"{_display_name(comment.author)} added a comment on {task.title}.",
        button_text="Open Discussion",
        button_url=_task_url(task=task, comment=comment),
        detail_title="Discussion details",
        detail_items=[
            {"label": "Task", "value": task.title},
            {"label": "Team", "value": task.team.name},
            {"label": "Commented by", "value": _display_name(comment.author)},
        ],
        preview_label="Comment preview",
        preview_text=_shorten_text(comment.content),
        footer_note="Open the task discussion to read the full thread and reply.",
        reason_text=f"You received this email because a task you are involved in has a new comment in {_get_app_name()}.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_COMMENT_POSTED,
        template_name="comment_posted",
        recipient_email=recipient.email,
        subject=f"New comment on {task.title}",
        context=context,
        metadata={"task_id": str(task.id), "comment_id": str(comment.id), "recipient_id": str(recipient.id)},
        dedupe_key=f"comment-posted:{comment.id}:{recipient.id}",
        source="comments.activity",
        related_object_type="comment",
        related_object_id=str(comment.id),
        provider_metadata={"categories": [EMAIL_TYPE_COMMENT_POSTED]},
    )


def build_mentioned_email_payload(*, comment, task, mentioned_user) -> QueuedEmailPayload:
    context = _base_context(
        eyebrow="Mention",
        title="You were mentioned in a comment",
        greeting=f"Hi {_display_name(mentioned_user, 'there')},",
        intro=f"{_display_name(comment.author)} mentioned you in a comment on {task.title}.",
        preheader_text=f"{_display_name(comment.author)} mentioned you on {task.title}.",
        button_text="View Comment",
        button_url=_task_url(task=task, comment=comment),
        detail_title="Discussion details",
        detail_items=[
            {"label": "Task", "value": task.title},
            {"label": "Team", "value": task.team.name},
            {"label": "Mentioned by", "value": _display_name(comment.author)},
        ],
        preview_label="Comment preview",
        preview_text=_shorten_text(comment.content),
        footer_note="Jump into the conversation to reply or clarify the next step.",
        reason_text=f"You received this email because you were mentioned in a workspace discussion in {_get_app_name()}.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_MENTIONED_IN_COMMENT,
        template_name="mentioned",
        recipient_email=mentioned_user.email,
        subject=f"You were mentioned in {task.title}",
        context=context,
        metadata={"task_id": str(task.id), "comment_id": str(comment.id), "recipient_id": str(mentioned_user.id)},
        dedupe_key=f"mention:{comment.id}:{mentioned_user.id}",
        source="comments.mentions",
        related_object_type="comment",
        related_object_id=str(comment.id),
        provider_metadata={"categories": [EMAIL_TYPE_MENTIONED_IN_COMMENT]},
    )


def build_welcome_email_payload(*, user, dashboard_url: str | None = None) -> QueuedEmailPayload:
    context = _base_context(
        eyebrow="Welcome",
        title=f"Welcome to {_get_app_name()}",
        greeting=f"Hi {_display_name(user, 'there')},",
        intro="Your account is ready. Open your workspace to create a team, join collaborators, and start tracking work.",
        preheader_text=f"Your {_get_app_name()} workspace is ready.",
        button_text="Open Dashboard",
        button_url=dashboard_url or _dashboard_url(),
        footer_note="We are glad to have you here.",
        reason_text=f"You received this email because a new {_get_app_name()} account was created with this address.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_WELCOME,
        template_name="welcome",
        recipient_email=user.email,
        subject=f"Welcome to {_get_app_name()}",
        context=context,
        metadata={"user_id": str(user.id)},
        source="authentication.welcome",
        related_object_type="user",
        related_object_id=str(user.id),
        provider_metadata={"categories": [EMAIL_TYPE_WELCOME]},
    )


def build_invitation_accepted_email_payload(*, invitation, recipient_user, actor) -> QueuedEmailPayload:
    context = _base_context(
        eyebrow="Team update",
        title="An invitation was accepted",
        greeting=f"Hi {_display_name(recipient_user, 'there')},",
        intro=f"{_display_name(actor)} accepted the invitation to join {invitation.team.name}.",
        preheader_text=f"{_display_name(actor)} joined {invitation.team.name}.",
        button_text="Open Team",
        button_url=_team_url(team=invitation.team),
        detail_title="Membership details",
        detail_items=[
            {"label": "Team", "value": invitation.team.name},
            {"label": "Accepted by", "value": _display_name(actor)},
            {"label": "Role", "value": invitation.get_role_display()},
        ],
        footer_note="Your team workspace is ready for the new member.",
        reason_text=f"You received this email because a pending team invitation was accepted in {_get_app_name()}.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_INVITATION_ACCEPTED,
        template_name="invitation_accepted",
        recipient_email=recipient_user.email,
        subject=f"Invitation accepted: {invitation.team.name}",
        context=context,
        metadata={"team_id": str(invitation.team_id), "invitation_id": str(invitation.id)},
        source="memberships.acceptance",
        related_object_type="team_invitation",
        related_object_id=str(invitation.id),
        provider_metadata={"categories": [EMAIL_TYPE_INVITATION_ACCEPTED]},
    )


def build_role_changed_email_payload(*, membership, actor, old_role: str, new_role: str) -> QueuedEmailPayload:
    context = _base_context(
        eyebrow="Role update",
        title="Your team role was updated",
        greeting=f"Hi {_display_name(membership.user, 'there')},",
        intro=f"{_display_name(actor)} updated your role in {membership.team.name}.",
        preheader_text=f"Your role in {membership.team.name} was updated.",
        button_text="Open Team",
        button_url=_team_url(team=membership.team),
        detail_title="Role details",
        detail_items=[
            {"label": "Team", "value": membership.team.name},
            {"label": "Previous role", "value": old_role.replace('_', ' ').title()},
            {"label": "New role", "value": new_role.replace('_', ' ').title()},
        ],
        footer_note="Role updates can change what you can manage inside the workspace.",
        reason_text=f"You received this email because your access level changed in {_get_app_name()}.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_ROLE_CHANGED,
        template_name="role_changed",
        recipient_email=membership.user.email,
        subject=f"Your role changed in {membership.team.name}",
        context=context,
        metadata={"team_id": str(membership.team_id), "membership_id": str(membership.id)},
        source="memberships.role_change",
        related_object_type="membership",
        related_object_id=str(membership.id),
        provider_metadata={"categories": [EMAIL_TYPE_ROLE_CHANGED]},
    )


def build_task_status_changed_email_payload(*, task, previous_status: str, changed_by, recipient) -> QueuedEmailPayload:
    context = _base_context(
        eyebrow="Task update",
        title="Task status updated",
        greeting=f"Hi {_display_name(recipient, 'there')},",
        intro=f"{_display_name(changed_by)} changed the status of {task.title}.",
        preheader_text=f"{task.title} changed from {previous_status.replace('_', ' ').title()} to {task.get_status_display()}.",
        button_text="Review Task",
        button_url=_task_url(task=task),
        detail_title="Status details",
        detail_items=[
            {"label": "Task", "value": task.title},
            {"label": "Previous status", "value": previous_status.replace('_', ' ').title()},
            {"label": "Current status", "value": task.get_status_display()},
            {"label": "Team", "value": task.team.name},
        ],
        footer_note="Open the task to review progress and next steps.",
        reason_text=f"You received this email because a task changed state in {_get_app_name()}.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_TASK_STATUS_CHANGED,
        template_name="task_status_changed",
        recipient_email=recipient.email,
        subject=f"Task status changed: {task.title}",
        context=context,
        metadata={"task_id": str(task.id), "team_id": str(task.team_id)},
        dedupe_key=f"task-status:{task.id}:{recipient.id}:{task.last_status_changed_at.isoformat() if task.last_status_changed_at else task.updated_at.isoformat()}",
        source="tasks.status_change",
        related_object_type="task",
        related_object_id=str(task.id),
        provider_metadata={"categories": [EMAIL_TYPE_TASK_STATUS_CHANGED]},
    )


def build_attachment_uploaded_email_payload(*, attachment, recipient) -> QueuedEmailPayload:
    context = _base_context(
        eyebrow="File update",
        title="New attachment uploaded",
        greeting=f"Hi {_display_name(recipient, 'there')},",
        intro=f"{_display_name(attachment.uploaded_by)} uploaded a file to {attachment.task.title}.",
        preheader_text=f"{attachment.original_name} was added to {attachment.task.title}.",
        button_text="Open Task",
        button_url=_task_url(task=attachment.task),
        detail_title="Attachment details",
        detail_items=[
            {"label": "Task", "value": attachment.task.title},
            {"label": "Team", "value": attachment.task.team.name},
            {"label": "File", "value": attachment.original_name},
            {"label": "Uploaded by", "value": _display_name(attachment.uploaded_by)},
        ],
        footer_note="Open the task to preview the attachment or continue the discussion.",
        reason_text=f"You received this email because a file was uploaded to a task you can access in {_get_app_name()}.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_ATTACHMENT_UPLOADED,
        template_name="attachment_uploaded",
        recipient_email=recipient.email,
        subject=f"Attachment uploaded: {attachment.original_name}",
        context=context,
        metadata={"attachment_id": str(attachment.id), "task_id": str(attachment.task_id)},
        dedupe_key=f"attachment-uploaded:{attachment.id}:{recipient.id}",
        source="attachments.upload",
        related_object_type="attachment",
        related_object_id=str(attachment.id),
        provider_metadata={"categories": [EMAIL_TYPE_ATTACHMENT_UPLOADED]},
    )


def build_notification_email_payload(*, notification) -> QueuedEmailPayload:
    task = _get_task_from_notification(notification=notification)
    comment = _get_comment_from_notification(notification=notification)
    invitation = _get_invitation_from_notification(notification=notification)

    if notification.type == NotificationType.TASK_ASSIGNED and task is not None:
        return build_task_assigned_email_payload(
            task=task,
            assigner=notification.actor or task.created_by,
            assignee=notification.user,
        )

    if notification.type == NotificationType.DEADLINE_APPROACHING and task is not None:
        reminder_window_hours = int((notification.metadata or {}).get("reminder_window_hours") or 24)
        return build_deadline_approaching_email_payload(
            task=task,
            recipient=notification.user,
            reminder_window_hours=reminder_window_hours,
        )

    if notification.type == NotificationType.COMMENT_POSTED and task is not None and comment is not None:
        return build_comment_posted_email_payload(comment=comment, task=task, recipient=notification.user)

    if notification.type == NotificationType.MENTIONED_IN_COMMENT and task is not None and comment is not None:
        return build_mentioned_email_payload(comment=comment, task=task, mentioned_user=notification.user)

    if notification.type == NotificationType.TEAM_INVITE and invitation is not None:
        return build_team_invite_email_payload(invitation=invitation)

    context = _base_context(
        eyebrow="Notification",
        title=notification.title,
        greeting=f"Hi {_display_name(notification.user, 'there')},",
        intro=notification.message,
        preheader_text=notification.message,
        button_text="Open Notification",
        button_url=_frontend_path("/notifications"),
        footer_note="Review the latest activity in your workspace.",
        reason_text=f"You received this email because of a new notification in {_get_app_name()}.",
    )
    return _build_job(
        email_type=EMAIL_TYPE_NOTIFICATION,
        template_name="notification",
        recipient_email=notification.user.email,
        subject=notification.title,
        context=context,
        metadata={"notification_id": str(notification.id)},
        dedupe_key=f"notification:{notification.id}",
        source="notifications.generic",
        related_object_type="notification",
        related_object_id=str(notification.id),
        provider_metadata={"categories": [EMAIL_TYPE_NOTIFICATION]},
    )


def _get_task_from_notification(*, notification):
    task_id = (notification.metadata or {}).get("task_id")
    if not task_id and notification.target_type == "task" and notification.target_id:
        task_id = str(notification.target_id)
    if not task_id:
        return None

    try:
        normalized_task_id = str(UUID(str(task_id)))
    except (TypeError, ValueError, AttributeError):
        return None

    from apps.tasks.models import Task

    return Task.objects.select_related("team", "assigned_to", "created_by").filter(id=normalized_task_id).first()


def _get_comment_from_notification(*, notification):
    comment_id = (notification.metadata or {}).get("comment_id")
    if not comment_id and notification.target_type == "comment" and notification.target_id:
        comment_id = str(notification.target_id)
    if not comment_id:
        return None

    from apps.comments.models import Comment

    return Comment.objects.select_related("author", "task__team", "task__assigned_to", "task__created_by").filter(id=comment_id).first()


def _get_invitation_from_notification(*, notification):
    invitation_token = (notification.metadata or {}).get("invitation_token")
    invitation_id = (notification.metadata or {}).get("invitation_id")

    from apps.memberships.models import TeamInvitation

    queryset = TeamInvitation.objects.select_related("team", "invited_by")
    if invitation_token:
        return queryset.filter(token=invitation_token).first()
    if invitation_id:
        return queryset.filter(id=invitation_id).first()
    return None
from uuid import UUID
