from django.urls import path

from apps.users.views import (
    AdminUserDetailView,
    AdminUserSearchView,
    NotificationPreferencesView,
    PhoneVerificationConfirmView,
    PhoneVerificationRequestView,
    PushDeviceDetailView,
    PushDeviceListCreateView,
    UserPhoneSettingsView,
    UserProfileView,
)

app_name = "users"

urlpatterns = [
    path("me/", UserProfileView.as_view(), name="me"),
    path("me/phone/", UserPhoneSettingsView.as_view(), name="me-phone"),
    path("me/phone/verify/request/", PhoneVerificationRequestView.as_view(), name="me-phone-verify-request"),
    path("me/phone/verify/confirm/", PhoneVerificationConfirmView.as_view(), name="me-phone-verify-confirm"),
    path("me/notification-preferences/", NotificationPreferencesView.as_view(), name="me-notification-preferences"),
    path("me/devices/", PushDeviceListCreateView.as_view(), name="devices"),
    path("me/devices/<uuid:pk>/", PushDeviceDetailView.as_view(), name="device-detail"),
    path("admin/search/", AdminUserSearchView.as_view(), name="admin-search"),
    path("admin/<uuid:pk>/", AdminUserDetailView.as_view(), name="admin-detail"),
]
