#!/bin/sh
set -e

OUTPUT_PATH="${1:-schema/openapi.yaml}"
OUTPUT_DIR="$(dirname "$OUTPUT_PATH")"

mkdir -p "$OUTPUT_DIR"
python manage.py spectacular --file "$OUTPUT_PATH" --validate
