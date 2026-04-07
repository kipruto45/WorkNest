from .base import *  # noqa: F403,F401

DEBUG = True

AUTH_COOKIE_SECURE = False
AUTH_COOKIE_SAMESITE = "Lax"

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
