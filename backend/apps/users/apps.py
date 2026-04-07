from django.apps import AppConfig
import logging
import sys


logger = logging.getLogger(__name__)


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    label = "users"
    verbose_name = "Users"
    _bootstrap_attempted = False

    def ready(self):
        if self._bootstrap_attempted:
            return
        self._bootstrap_attempted = True

        management_commands_to_skip = {"makemigrations", "migrate", "collectstatic", "test", "shell"}
        if any(arg in management_commands_to_skip for arg in sys.argv[1:]):
            return

        try:
            from apps.users.services import bootstrap_admin_user_from_settings

            result = bootstrap_admin_user_from_settings()
            if result is not None:
                user, created = result
                logger.info(
                    "admin_bootstrap_completed",
                    extra={"email": user.email, "created": created},
                )
        except Exception:
            logger.exception("admin_bootstrap_failed")
