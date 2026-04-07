#!/bin/sh
set -eu

OUTPUT_PATH="${1:-schema/openapi.json}"
OUTPUT_DIR="$(dirname "$OUTPUT_PATH")"
TMP_PATH="${OUTPUT_PATH}.tmp"

mkdir -p "$OUTPUT_DIR"

if python manage.py spectacular --file "$TMP_PATH"; then
  mv "$TMP_PATH" "$OUTPUT_PATH"
  echo "OpenAPI schema exported to $OUTPUT_PATH"
else
  rm -f "$TMP_PATH"
  echo "OpenAPI schema export failed; continuing without generated schema." >&2
fi
