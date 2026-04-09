from django.urls import path

from apps.integrations.calendar_views import (
    CalendarImportConfirmView,
    CalendarImportPreviewView,
    CalendarTaskExportICSView,
    GoogleCalendarCallbackView,
    GoogleCalendarConnectView,
    GoogleCalendarDisconnectView,
    GoogleCalendarImportPreviewView,
    GoogleCalendarListView,
    GoogleCalendarSelectView,
    GoogleCalendarStatusView,
    GoogleCalendarSyncTasksView,
)

app_name = "calendar"

urlpatterns = [
    path("export/ics/", CalendarTaskExportICSView.as_view(), name="export-ics"),
    path("import/preview/", CalendarImportPreviewView.as_view(), name="import-preview"),
    path("import/confirm/", CalendarImportConfirmView.as_view(), name="import-confirm"),
    path("google/connect/", GoogleCalendarConnectView.as_view(), name="google-connect"),
    path("google/callback/", GoogleCalendarCallbackView.as_view(), name="google-callback"),
    path("google/status/", GoogleCalendarStatusView.as_view(), name="google-status"),
    path("google/calendars/", GoogleCalendarListView.as_view(), name="google-calendars"),
    path("google/select-calendar/", GoogleCalendarSelectView.as_view(), name="google-select-calendar"),
    path("google/disconnect/", GoogleCalendarDisconnectView.as_view(), name="google-disconnect"),
    path("google/sync/", GoogleCalendarSyncTasksView.as_view(), name="google-sync"),
    path("google/import/preview/", GoogleCalendarImportPreviewView.as_view(), name="google-import-preview"),
]
