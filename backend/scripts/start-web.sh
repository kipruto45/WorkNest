#!/bin/sh
set -e

PORT="${PORT:-8000}"
APP_SERVER="${APP_SERVER:-daphne}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-3}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  python manage.py migrate --noinput
fi

if [ "${ADMIN_BOOTSTRAP_ENABLED:-0}" = "1" ]; then
  python manage.py ensure_admin_user \
    --email "${ADMIN_EMAIL:-admin@worknest.local}" \
    --name "${ADMIN_NAME:-WorkNest Admin}" \
    --password "${ADMIN_PASSWORD:-WorkNest123!}"
fi

if [ "${RUN_COLLECTSTATIC:-1}" = "1" ]; then
  python manage.py collectstatic --noinput
fi

case "$APP_SERVER" in
  gunicorn)
    exec gunicorn config.asgi:application \
      --worker-class uvicorn.workers.UvicornWorker \
      --bind "0.0.0.0:${PORT}" \
      --workers "${WEB_CONCURRENCY}" \
      --timeout "${GUNICORN_TIMEOUT}"
    ;;
  uvicorn)
    exec uvicorn config.asgi:application --host 0.0.0.0 --port "${PORT}"
    ;;
  daphne)
    exec daphne -b 0.0.0.0 -p "${PORT}" config.asgi:application
    ;;
  *)
    echo "Unsupported APP_SERVER: ${APP_SERVER}" >&2
    exit 1
    ;;
esac
