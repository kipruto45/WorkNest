#!/bin/sh
set -e

exec celery -A config beat \
  -l "${CELERY_LOGLEVEL:-info}" \
  --schedule "${CELERY_BEAT_SCHEDULE_FILE:-/tmp/celerybeat-schedule}"
