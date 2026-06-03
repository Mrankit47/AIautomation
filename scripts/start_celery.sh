#!/bin/bash
set -e

echo "Starting Celery worker..."
exec celery -A backend.tasks.celery_app:celery_app worker \
  --loglevel=INFO \
  --queues=artwork,workflow \
  --concurrency=4
