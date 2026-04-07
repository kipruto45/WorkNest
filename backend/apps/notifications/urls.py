from django.urls import path

from apps.notifications.views import (
    AdminNotificationSendView,
    NotificationDetailView,
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationMarkUnreadView,
    NotificationUnreadCountView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("admin/send/", AdminNotificationSendView.as_view(), name="admin-send"),
    path("unread-count/", NotificationUnreadCountView.as_view(), name="unread-count"),
    path("mark-all-read/", NotificationMarkAllReadView.as_view(), name="mark-all-read"),
    path("<uuid:pk>/", NotificationDetailView.as_view(), name="detail"),
    path("<uuid:pk>/read/", NotificationMarkReadView.as_view(), name="mark-read"),
    path("<uuid:pk>/unread/", NotificationMarkUnreadView.as_view(), name="mark-unread"),
]
