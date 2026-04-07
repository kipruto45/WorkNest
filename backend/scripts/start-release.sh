#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${ADMIN_BOOTSTRAP_ENABLED:-0}" = "1" ]; then
  python manage.py ensure_admin_user \
    --email "${ADMIN_EMAIL:-kiprutovictor39@gmail.com}" \
    --name "${ADMIN_NAME:-WorkNest Admin}" \
    --password "${ADMIN_PASSWORD:-WorkNest123!}"
fi

if [ "${EXPORT_OPENAPI_ON_BOOT:-1}" = "1" ]; then
  /app/scripts/export-openapi.sh /app/schema/openapi.json
fi
