from django.urls import path

from apps.notifications.views import (
    AdminCommunicationDetailView,
    AdminCommunicationListCreateView,
    AdminNotificationSendView,
    AdminSMSLogDetailView,
    AdminSMSLogListView,
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
    path("admin/communications/", AdminCommunicationListCreateView.as_view(), name="admin-communications"),
    path("admin/communications/<uuid:pk>/", AdminCommunicationDetailView.as_view(), name="admin-communication-detail"),
    path("admin/sms-logs/", AdminSMSLogListView.as_view(), name="admin-sms-logs"),
    path("admin/sms-logs/<uuid:pk>/", AdminSMSLogDetailView.as_view(), name="admin-sms-log-detail"),
    path("unread-count/", NotificationUnreadCountView.as_view(), name="unread-count"),
    path("mark-all-read/", NotificationMarkAllReadView.as_view(), name="mark-all-read"),
    path("<uuid:pk>/", NotificationDetailView.as_view(), name="detail"),
    path("<uuid:pk>/read/", NotificationMarkReadView.as_view(), name="mark-read"),
    path("<uuid:pk>/unread/", NotificationMarkUnreadView.as_view(), name="mark-unread"),
]
