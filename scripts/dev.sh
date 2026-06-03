#!/bin/bash
set -e

echo "Running Alembic migrations in development mode..."
alembic upgrade head

echo "Starting development server with hot-reload..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
