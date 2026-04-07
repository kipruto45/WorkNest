from django.urls import path

from apps.users.views import AdminUserSearchView, UserProfileView

app_name = "users"

urlpatterns = [
    path("me/", UserProfileView.as_view(), name="me"),
    path("admin/search/", AdminUserSearchView.as_view(), name="admin-search"),
]
