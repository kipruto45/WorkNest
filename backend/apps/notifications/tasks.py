from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from celery import shared_task

from apps.integrations.email.services import send_notification_email
from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification
from apps.tasks.models import Task


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_notification_email_task(self, notification_id: str) -> bool:
    notification = (
        Notification.objects.select_related("user", "actor", "team")
        .filter(id=notification_id)
        .first()
    )
    if not notification or not notification.user.email:
        return False

    send_notification_email(notification=notification)
    return True


@shared_task
def send_deadline_approaching_notifications_task() -> int:
    from apps.notifications.services import notify_deadline_approaching

    now = timezone.now()
    created_count = 0
    reminder_windows = [int(value) for value in getattr(settings, "NOTIFICATION_DEADLINE_REMINDER_WINDOWS_HOURS", [24])]
    grace_minutes = int(getattr(settings, "NOTIFICATION_DEADLINE_REMINDER_GRACE_MINUTES", 30))

    for reminder_hours in reminder_windows:
        window_start = now + timedelta(hours=reminder_hours) - timedelta(minutes=grace_minutes)
        window_end = now + timedelta(hours=reminder_hours) + timedelta(minutes=grace_minutes)

        tasks = (
            Task.objects.select_related("assigned_to", "team", "created_by")
            .filter(
                assigned_to__isnull=False,
                team__is_archived=False,
                is_archived=False,
                due_date__isnull=False,
                due_date__gte=window_start,
                due_date__lte=window_end,
            )
            .exclude(status=Task.Status.DONE)
        )

        for task in tasks:
            notification = notify_deadline_approaching(task=task, reminder_window_hours=reminder_hours)
            if notification is not None:
                created_count += 1
    return created_count
