#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${ADMIN_BOOTSTRAP_ENABLED:-0}" = "1" ]; then
  if [ -z "${ADMIN_EMAIL:-}" ] || [ -z "${ADMIN_PASSWORD:-}" ]; then
    echo "ADMIN_EMAIL and ADMIN_PASSWORD must be set when ADMIN_BOOTSTRAP_ENABLED=1." >&2
    exit 1
  fi
  python manage.py ensure_admin_user \
    --email "${ADMIN_EMAIL}" \
    --name "${ADMIN_NAME:-WorkNest Admin}" \
    --password "${ADMIN_PASSWORD}"
fi

if [ "${EXPORT_OPENAPI_ON_BOOT:-1}" = "1" ]; then
  /app/scripts/export-openapi.sh /app/schema/openapi.json
fi
