from .base import *  # noqa: F403,F401

DEBUG = True

AUTH_COOKIE_SECURE = False
AUTH_COOKIE_SAMESITE = "Lax"

# Manual local development should work without requiring a separate Postgres
# service. Docker Compose overrides POSTGRES_HOST to `postgres`, so it will
# continue using the containerized Postgres database instead of SQLite.
_local_database_url = env("DATABASE_URL", default="").strip()
_local_postgres_host = env("POSTGRES_HOST", default=env("DB_HOST", default="")).strip().lower()
if not _local_database_url and _local_postgres_host in {"", "localhost", "127.0.0.1"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "dev.sqlite3",
        }
    }

# Local development should not require Redis or a running Celery worker just to boot
# the app shell and exercise the main product flows.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "worknest-local-cache",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
