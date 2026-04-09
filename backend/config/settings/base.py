from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlparse
from pathlib import Path
from email.utils import formataddr

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DEBUG=(bool, False),
    ENVIRONMENT=(str, "local"),
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000", "http://localhost:5173"]),
    CSRF_TRUSTED_ORIGINS=(list, ["http://localhost:3000", "http://localhost:5173"]),
    DATABASE_CONN_MAX_AGE=(int, 60),
    DATABASE_SSL_REQUIRE=(bool, False),
    HEALTH_REQUIRE_CACHE=(bool, False),
    REDIS_HOST=(str, "localhost"),
    REDIS_PORT=(int, 6379),
    ACCESS_TOKEN_LIFETIME_MINUTES=(int, 15),
    REFRESH_TOKEN_LIFETIME_DAYS=(int, 7),
    DEFAULT_FROM_EMAIL=(str, "no-reply@example.com"),
    EMAIL_FROM_NAME=(str, "WorkNest"),
    EMAIL_PROVIDER=(str, "smtp"),
    EMAIL_DELIVERY_MODE=(str, "sync"),
    EMAIL_BACKEND=(str, "django.core.mail.backends.console.EmailBackend"),
    EMAIL_HOST=(str, "localhost"),
    EMAIL_PORT=(int, 1025),
    EMAIL_HOST_USER=(str, ""),
    EMAIL_HOST_PASSWORD=(str, ""),
    EMAIL_USE_TLS=(bool, False),
    EMAIL_USE_SSL=(bool, False),
    SMTP_HOST=(str, ""),
    SMTP_PORT=(int, 0),
    SMTP_USERNAME=(str, ""),
    SMTP_PASSWORD=(str, ""),
    SENDGRID_API_KEY=(str, ""),
    GOOGLE_CLIENT_ID=(str, ""),
    GOOGLE_CLIENT_SECRET=(str, ""),
    GOOGLE_REDIRECT_URI=(str, ""),
    FRONTEND_URL=(str, "http://localhost:5173"),
    PUBLIC_WEBAPP_URL=(str, ""),
    BACKEND_URL=(str, "http://localhost:8000"),
    INVITE_LINK_BASE_URL=(str, ""),
    PASSWORD_RESET_LINK_BASE_URL=(str, ""),
    LOGO_URL=(str, ""),
    NOTIFICATION_EMAIL_ENABLED=(bool, True),
    NOTIFICATION_EMAIL_TYPES=(list, ["task_assigned", "mentioned_in_comment", "deadline_approaching", "comment_posted"]),
    NOTIFICATION_SMS_ENABLED=(bool, True),
    NOTIFICATION_SMS_TYPES=(list, ["task_assigned", "mentioned_in_comment", "deadline_approaching", "team_invite", "admin_message"]),
    NOTIFICATION_DEADLINE_REMINDER_HOURS=(int, 24),
    NOTIFICATION_DEADLINE_REMINDER_WINDOWS_HOURS=(list, ["24", "1"]),
    NOTIFICATION_DEADLINE_REMINDER_GRACE_MINUTES=(int, 30),
    EMAIL_TASK_MAX_RETRIES=(int, 3),
    EMAIL_RETRY_BACKOFF_SECONDS=(int, 2),
    WELCOME_EMAIL_ENABLED=(bool, True),
    SMS_PROVIDER=(str, "africas_talking"),
    SMS_ENABLED=(bool, False),
    SMS_MAX_RETRIES=(int, 3),
    SMS_RETRY_BACKOFF_SECONDS=(int, 2),
    SMS_BROADCAST_CONFIRMATION_REQUIRED=(bool, True),
    SMS_REQUIRE_VERIFIED_PHONE=(bool, False),
    SMS_USE_SANDBOX=(str, ""),
    DEFAULT_COUNTRY_CODE=(str, "+254"),
    AFRICAS_TALKING_USERNAME=(str, ""),
    AFRICAS_TALKING_API_KEY=(str, ""),
    AFRICAS_TALKING_SENDER_ID=(str, ""),
    AFRICAS_TALKING_USE_SANDBOX=(str, ""),
    AFRICAS_TALKING_ENVIRONMENT=(str, "sandbox"),
    AFRICAS_TALKING_BASE_URL=(str, ""),
    AUTH_REFRESH_COOKIE_NAME=(str, "refresh_token"),
    AUTH_REFRESH_COOKIE_PATH=(str, "/api/v1/auth/"),
    AUTH_COOKIE_SECURE=(bool, False),
    AUTH_COOKIE_SAMESITE=(str, "Lax"),
    STATIC_URL=(str, "/static/"),
    MEDIA_URL=(str, "/media/"),
    FILES_URL=(str, "/files/"),
    ATTACHMENTS_STORAGE_BACKEND=(str, "local"),
    ATTACHMENTS_MAX_FILE_SIZE=(int, 10 * 1024 * 1024),
    ATTACHMENTS_SUPABASE_BUCKET=(str, "task-attachments"),
    ATTACHMENTS_SIGNED_URL_TTL=(int, 300),
    DB_NAME=(str, "worknest"),
    DB_USER=(str, "postgres"),
    DB_PASSWORD=(str, "postgres"),
    DB_HOST=(str, "localhost"),
    DB_PORT=(str, "5432"),
    DB_SSL_MODE=(str, ""),
    SUPABASE_SERVICE_ROLE_KEY=(str, ""),
    SUPABASE_TIMEOUT=(int, 30),
)

environ.Env.read_env(BASE_DIR / ".env")


def _parse_host_from_url(value: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ""
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    return (parsed.hostname or "").strip()


def _merge_unique_strings(*groups: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            candidate = str(item or "").strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            results.append(candidate)
    return results


def build_database_config() -> dict:
    database_url = env("DATABASE_URL", default=None)
    if database_url:
        database_config = env.db("DATABASE_URL", default=database_url)
    else:
        database_config = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", default=env("DB_NAME")),
            "USER": env("POSTGRES_USER", default=env("DB_USER")),
            "PASSWORD": env("POSTGRES_PASSWORD", default=env("DB_PASSWORD")),
            "HOST": env("POSTGRES_HOST", default=env("DB_HOST")),
            "PORT": env("POSTGRES_PORT", default=env("DB_PORT")),
        }

    database_config["CONN_MAX_AGE"] = env("DATABASE_CONN_MAX_AGE")
    db_ssl_mode = env("DB_SSL_MODE", default="").strip().lower()
    if env("DATABASE_SSL_REQUIRE") or db_ssl_mode == "require":
        database_config.setdefault("OPTIONS", {})
        database_config["OPTIONS"]["sslmode"] = "require"
    return database_config


SECRET_KEY = env("SECRET_KEY", default="unsafe-development-key")
DEBUG = env("DEBUG")
ENVIRONMENT = env("ENVIRONMENT")
API_VERSION = "v1"

_configured_allowed_hosts = env("ALLOWED_HOSTS")
_derived_allowed_hosts = _merge_unique_strings(
    _configured_allowed_hosts,
    [
        _parse_host_from_url(env("BACKEND_URL")),
        _parse_host_from_url(env("FRONTEND_URL")),
        _parse_host_from_url(env("PUBLIC_WEBAPP_URL")),
        str(env("RENDER_EXTERNAL_HOSTNAME", default="")).strip(),
        "127.0.0.1",
        "localhost",
    ],
)
ALLOWED_HOSTS = _derived_allowed_hosts or ["127.0.0.1", "localhost"]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "django_filters",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "channels",
]

LOCAL_APPS = [
    "apps.common.apps.CommonConfig",
    "apps.core.apps.CoreConfig",
    "apps.authentication.apps.AuthenticationConfig",
    "apps.users.apps.UsersConfig",
    "apps.teams.apps.TeamsConfig",
    "apps.memberships.apps.MembershipsConfig",
    "apps.tasks.apps.TasksConfig",
    "apps.comments.apps.CommentsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.realtime.apps.RealtimeConfig",
    "apps.attachments.apps.AttachmentsConfig",
    "apps.dashboards.apps.DashboardsConfig",
    "apps.audit_logs.apps.AuditLogsConfig",
    "apps.integrations.apps.IntegrationsConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "apps.common.middleware.RequestIDMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "apps.common.middleware.RequestLogMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.audit_logs.middleware.AuditLogContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

DATABASES = {"default": build_database_config()}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "users.User"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = env("STATIC_URL")
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "files"]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
MEDIA_URL = env("MEDIA_URL")
MEDIA_ROOT = BASE_DIR / "media"
FILES_URL = env("FILES_URL")
FILES_ROOT = BASE_DIR / "files"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_ID = 1

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultPageNumberPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    )
    if DEBUG
    else (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "apps.common.throttles.AnonRateThrottle",
        "apps.common.throttles.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "120/minute",
        "auth_login": "10/hour",
        "auth_register": "5/hour",
        "auth_password_reset": "5/hour",
        "auth_phone_verification": "5/hour",
        "admin_sms_broadcast": "10/hour",
    },
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "WorkNest API",
    "DESCRIPTION": "Foundation API schema for the backend platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("ACCESS_TOKEN_LIFETIME_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("REFRESH_TOKEN_LIFETIME_DAYS")),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
)

CORS_ALLOW_CREDENTIALS = True
_configured_cors_origins = env("CORS_ALLOWED_ORIGINS")
_derived_browser_origins = _merge_unique_strings(
    _configured_cors_origins,
    [
        str(env("FRONTEND_URL")).strip(),
        str(env("PUBLIC_WEBAPP_URL")).strip(),
        "http://localhost:3000",
        "http://localhost:5173",
    ],
)
CORS_ALLOWED_ORIGINS = _derived_browser_origins
CSRF_TRUSTED_ORIGINS = _merge_unique_strings(env("CSRF_TRUSTED_ORIGINS"), _derived_browser_origins)

REDIS_HOST = env("REDIS_HOST")
REDIS_PORT = env("REDIS_PORT")
REDIS_URL = env("REDIS_URL", default=f"redis://{REDIS_HOST}:{REDIS_PORT}/1")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    },
    "throttle": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "worknest-throttle-cache",
    },
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = True

EMAIL_PROVIDER = env("EMAIL_PROVIDER")
EMAIL_DELIVERY_MODE = env("EMAIL_DELIVERY_MODE", default="sync").strip().lower() or "sync"
_CONFIGURED_EMAIL_BACKEND = env("EMAIL_BACKEND", default="").strip()
if _CONFIGURED_EMAIL_BACKEND:
    EMAIL_BACKEND = _CONFIGURED_EMAIL_BACKEND
elif EMAIL_PROVIDER == "smtp":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_FROM_NAME = env("EMAIL_FROM_NAME")
DEFAULT_FROM_EMAIL = formataddr((EMAIL_FROM_NAME, env("DEFAULT_FROM_EMAIL")))
EMAIL_HOST = env("SMTP_HOST") or env("EMAIL_HOST")
EMAIL_PORT = env("SMTP_PORT") or env("EMAIL_PORT")
EMAIL_HOST_USER = env("SMTP_USERNAME") or env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("SMTP_PASSWORD") or env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env("EMAIL_USE_TLS")
EMAIL_USE_SSL = env("EMAIL_USE_SSL")
SENDGRID_API_KEY = env("SENDGRID_API_KEY")

GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default=env("GOOGLE_CLIENT_ID", default=""))
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET", default=env("GOOGLE_CLIENT_SECRET", default=""))
GOOGLE_REDIRECT_URI = env("GOOGLE_REDIRECT_URI", default="")
SUPABASE_URL = env("SUPABASE_URL", default="")
SUPABASE_SERVICE_ROLE_KEY = env("SUPABASE_SERVICE_ROLE_KEY", default="")
SUPABASE_KEY = env("SUPABASE_KEY", default=SUPABASE_SERVICE_ROLE_KEY)
SUPABASE_ANON_KEY = env("SUPABASE_ANON_KEY", default="")
SUPABASE_TIMEOUT = env("SUPABASE_TIMEOUT")
ATTACHMENTS_STORAGE_BACKEND = env("ATTACHMENTS_STORAGE_BACKEND")
ATTACHMENTS_MAX_FILE_SIZE = env("ATTACHMENTS_MAX_FILE_SIZE")
ATTACHMENTS_SUPABASE_BUCKET = env("ATTACHMENTS_SUPABASE_BUCKET")
ATTACHMENTS_SIGNED_URL_TTL = env("ATTACHMENTS_SIGNED_URL_TTL")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "apps.core.logging.RequestIDLogFilter",
        }
    },
    "formatters": {
        "verbose": {
            "format": (
                "%(levelname)s %(asctime)s request_id=%(request_id)s "
                "method=%(method)s path=%(path)s status=%(status_code)s "
                "duration_ms=%(duration_ms)s %(name)s %(message)s"
            ),
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["request_id"],
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

FRONTEND_URL = env("FRONTEND_URL")
PUBLIC_WEBAPP_URL = env("PUBLIC_WEBAPP_URL", default="").strip()
BACKEND_URL = env("BACKEND_URL")
INVITE_LINK_BASE_URL = env("INVITE_LINK_BASE_URL", default=f"{FRONTEND_URL.rstrip('/')}/invitations")
PASSWORD_RESET_LINK_BASE_URL = env("PASSWORD_RESET_LINK_BASE_URL", default=f"{FRONTEND_URL.rstrip('/')}/reset-password")
APP_NAME = env("APP_NAME", default="WorkNest")
SUPPORT_EMAIL = env("SUPPORT_EMAIL", default=DEFAULT_FROM_EMAIL)
LOGO_URL = env("LOGO_URL", default="")
HEALTH_REQUIRE_CACHE = env("HEALTH_REQUIRE_CACHE")
NOTIFICATION_EMAIL_ENABLED = env("NOTIFICATION_EMAIL_ENABLED")
NOTIFICATION_EMAIL_TYPES = env("NOTIFICATION_EMAIL_TYPES")
NOTIFICATION_SMS_ENABLED = env("NOTIFICATION_SMS_ENABLED")
NOTIFICATION_SMS_TYPES = env("NOTIFICATION_SMS_TYPES")
NOTIFICATION_DEADLINE_REMINDER_HOURS = env("NOTIFICATION_DEADLINE_REMINDER_HOURS")
NOTIFICATION_DEADLINE_REMINDER_WINDOWS_HOURS = [int(value) for value in env("NOTIFICATION_DEADLINE_REMINDER_WINDOWS_HOURS")]
NOTIFICATION_DEADLINE_REMINDER_GRACE_MINUTES = env("NOTIFICATION_DEADLINE_REMINDER_GRACE_MINUTES")
EMAIL_TASK_MAX_RETRIES = env("EMAIL_TASK_MAX_RETRIES")
EMAIL_RETRY_BACKOFF_SECONDS = env("EMAIL_RETRY_BACKOFF_SECONDS")
WELCOME_EMAIL_ENABLED = env("WELCOME_EMAIL_ENABLED")
SMS_PROVIDER = env("SMS_PROVIDER")
SMS_ENABLED = env("SMS_ENABLED")
SMS_MAX_RETRIES = env("SMS_MAX_RETRIES")
SMS_RETRY_BACKOFF_SECONDS = env("SMS_RETRY_BACKOFF_SECONDS")
SMS_BROADCAST_CONFIRMATION_REQUIRED = env("SMS_BROADCAST_CONFIRMATION_REQUIRED")
SMS_REQUIRE_VERIFIED_PHONE = env("SMS_REQUIRE_VERIFIED_PHONE")
SMS_USE_SANDBOX = env("SMS_USE_SANDBOX", default="")
DEFAULT_COUNTRY_CODE = env("DEFAULT_COUNTRY_CODE")
AFRICAS_TALKING_USERNAME = env("AFRICAS_TALKING_USERNAME")
AFRICAS_TALKING_API_KEY = env("AFRICAS_TALKING_API_KEY")
AFRICAS_TALKING_SENDER_ID = env("AFRICAS_TALKING_SENDER_ID")
AFRICAS_TALKING_USE_SANDBOX = env("AFRICAS_TALKING_USE_SANDBOX", default=SMS_USE_SANDBOX)
AFRICAS_TALKING_ENVIRONMENT = env("AFRICAS_TALKING_ENVIRONMENT")
AFRICAS_TALKING_BASE_URL = env("AFRICAS_TALKING_BASE_URL")
AUTH_REFRESH_COOKIE_NAME = env("AUTH_REFRESH_COOKIE_NAME")
AUTH_REFRESH_COOKIE_PATH = env("AUTH_REFRESH_COOKIE_PATH")
AUTH_COOKIE_SECURE = env("AUTH_COOKIE_SECURE")
AUTH_COOKIE_HTTPONLY = True
AUTH_COOKIE_SAMESITE = env("AUTH_COOKIE_SAMESITE")
