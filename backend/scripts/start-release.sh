#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "${EXPORT_OPENAPI_ON_BOOT:-1}" = "1" ]; then
  /app/scripts/export-openapi.sh /app/schema/openapi.json
fi
