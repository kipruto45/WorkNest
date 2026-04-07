from django.urls import include, path

from apps.authentication.views import (
    GoogleAuthView,
    GoogleOAuthCallbackView,
    GoogleOAuthConfigView,
    GoogleLoginView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshTokenView,
    RegisterView,
)

app_name = "authentication"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", RefreshTokenView.as_view(), name="token-refresh"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("me/", MeView.as_view(), name="me"),
    path("google/config/", GoogleOAuthConfigView.as_view(), name="google-config"),
    path("google/login/", GoogleLoginView.as_view(), name="google-login"),
    path("google/auth/", GoogleAuthView.as_view(), name="google-auth"),
    path("google/callback/", GoogleOAuthCallbackView.as_view(), name="google-callback"),
    path("oauth/", include("allauth.urls")),
]
