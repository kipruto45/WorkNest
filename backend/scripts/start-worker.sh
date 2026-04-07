#!/bin/sh
set -e

exec celery -A config worker \
  -l "${CELERY_LOGLEVEL:-info}" \
  --concurrency "${CELERY_WORKER_CONCURRENCY:-2}"
