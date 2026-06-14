#!/bin/bash
set -e

# ── 1. Start Local Redis Server ──
echo "Starting local Redis server..."
redis-server --daemonize yes --port 6379

# Wait for redis to be ready
until redis-cli ping; do
  echo "Waiting for Redis to start..."
  sleep 1
done
echo "Redis is ready!"

# ── 2. Run database migrations ──
echo "Running database migrations..."
alembic upgrade head

# ── 3. Start Celery worker in the background ──
echo "Starting Celery worker in background..."
# Using concurrency=2 to fit safely within Render's Free Tier memory limits (512MB RAM)
celery -A backend.tasks.celery_app:celery_app worker \
  --loglevel=INFO \
  --queues=artwork,workflow \
  --concurrency=2 &

# ── 4. Start FastAPI server in the foreground ──
echo "Starting FastAPI app in foreground..."
exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
