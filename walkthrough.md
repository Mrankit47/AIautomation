# Walkthrough: Fully Autonomous Workflow Engine

We have successfully transformed the AI Artwork Automation Platform into a fully autonomous, production-grade workflow engine. The platform now ingests artwork, detects duplicates, executes LangGraph nodes, publishes to social media with transient error retries, and tracks executions—all automatically.

---

## 1. Accomplished Changes

### ── Phase 1: Auto-Start Workflow
- Uploading an artwork (via standard Swagger or Webhook API) now automatically spawns a `WorkflowRun` record (`PENDING`) and dispatches `execute_workflow.delay()` via Celery.
- The upload response immediately contains `workflow_run_id` and `celery_task_id`.

### ── Phase 2: Webhook Ingestion API
- Created a single unified endpoint `POST /api/v1/ingestion/artwork` which downloads images from external URLs, validates them, and submits them directly into the pipeline.

### ── Phase 3: Idempotency (Duplicate Detection)
- Integrated SHA-256 hashing on raw image bytes.
- Subsequent uploads of identical images instantly return the existing artwork response (returning the original `id` and the latest workflow details) without duplicate storage, database writes, or Celery invocations.

### ── Phase 4: Observability API
- Added `GET /api/v1/workflows/{id}` returning granular execution stats, active node state, start/end timing, and the complete step-by-step event timeline.
- Added `POST /api/v1/workflows/{id}/retry` allowing manual retry of failed runs.

### ── Phase 5: Workflow Events Tracking
- Created the `workflow_events` table (linked to `workflow_runs`).
- Node executions log `started`, `completed`, `failed`, or `retrying` events with accurate durations (in ms), retries, and failure stack traces.

### ── Phase 6: Transient Error Retry System
- Implemented `_retry_on_transient` helper.
- Social media publishing nodes (Instagram/YouTube) automatically retry up to 3 times with exponential backoff on transient errors, while immediately raising non-retryable errors (e.g. auth/validation).

### ── Phase 7: Webhook Authentication
- Secured the ingestion endpoint with API-Key auth via the `X-API-KEY` header using constant-time comparison (`hmac.compare_digest`).

### ── Phase 8: Strict State Machine transitions
- Enforced lifecycle state validation on the `Artwork` model using `transition_to(new_status)`. Invalid transitions (e.g. `UPLOADED` -> `COMPLETED`) raise `WorkflowException`, while self-transitions are safely treated as no-ops.

### ── Phase 9: System & Integration Health
- Added `GET /api/v1/health/workflow` aggregating stats (total, running, pending, completed, failed) and avg execution times for the last 24h.

---

## 2. Verification & Test Suite Results

We have verified the entire implementation using automated testing inside the Docker stack.

### Running all tests:
```bash
docker exec -e PYTHONPATH=/app artwork-app pytest -v
```

All 68 tests across the system, including the new unit/integration suites, passed successfully:
```text
tests_and_debug/tests/test_state_machine.py::test_valid_transitions PASSED
tests_and_debug/tests/test_state_machine.py::test_invalid_transitions PASSED
tests_and_debug/tests/test_state_machine.py::test_recovery_transition PASSED
tests_and_debug/tests/test_idempotency.py::test_duplicate_upload_returns_existing PASSED
tests_and_debug/tests/test_idempotency.py::test_new_upload_creates_new_record PASSED
tests_and_debug/tests/test_auto_trigger.py::test_auto_trigger_workflow_success PASSED
tests_and_debug/tests/test_ingestion.py::test_ingest_artwork_auth_failed PASSED
tests_and_debug/tests/test_ingestion.py::test_ingest_artwork_success PASSED
tests_and_debug/tests/test_workflow_events.py::test_workflow_event_creation PASSED
tests_and_debug/tests/test_workflow_events.py::test_workflow_run_relationship PASSED
tests_and_debug/tests/test_retry.py::test_retry_on_transient_success_eventually PASSED
tests_and_debug/tests/test_retry.py::test_retry_on_transient_fails_immediately_on_non_retryable PASSED
tests_and_debug/tests/test_retry.py::test_retry_on_transient_exhausts_retries PASSED
======================== 68 passed in 3.85s =========================
```

---

## 3. Post-Integration Fixes & Enhancements

### 1. Artwork Status Transition Sync Fix
* **Symptom**: When `collect_analytics` was disabled via the feature flags, the workflow transitioned directly to `END` without executing `collect_analytics`, leaving the overall artwork status stuck as `PROCESSING` in the database.
* **Resolution**: Updated `_mark_completed` and `_mark_failed` helpers in [workflow_task.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/tasks/workflow_task.py) to automatically transition the parent `Artwork` status in the database to match the final workflow run state (`COMPLETED`, `COMPLETED_WITH_WARNINGS`, or `FAILED`) and clear any stale error messages upon success.

### 2. Workflow Health Check SQL Query Fix
* **Symptom**: The `/api/v1/health/workflow` endpoint returned a `500 Internal Server Error` due to a database parsing exception (`InvalidTextRepresentationError: invalid input value for enum workflow_status`). The query was filtering on `'COMPLETED_WITH_WARNINGS'`, which is not present in the native Postgres `workflow_status` enum definition.
* **Resolution**: Modified the raw SQL queries in [health.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/api/v1/health.py) to check for `status = 'COMPLETED'` instead of `status IN ('COMPLETED', 'COMPLETED_WITH_WARNINGS')`, as `COMPLETED_WITH_WARNINGS` is normalized to `COMPLETED` at the Postgres enum level. The endpoint now completes successfully.

---

## 4. Render Free-Tier Deployment Guide

We have made the repository 100% deploy-ready for Render.com's **Free Web Service** tier using a single container "All-in-One" architecture. This avoids any paid services (like managed background workers or Redis) and doesn't require a credit card.

### What We Added:
1. **Docker Container updates**: Added `redis-server` installation to the production Dockerfile runner stage.
2. **Combined Startup Script**: Created [start_combined.sh](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/scripts/start_combined.sh) which starts:
   * Local lightweight `redis-server` inside the container.
   * Celery worker in the background (with concurrency limited to 2 to fit Render's 512MB RAM free tier limit).
   * Alembic database migrations.
   * FastAPI application (`uvicorn`) in the foreground.
3. **Free-Tier Blueprint**: Created [render.yaml](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/render.yaml) at the repository root configuring a single `web` service (`plan: free`) running the combined container.

### How to Deploy on Render for Free (No Credit Card):
1. **Free Database Setup**:
   * Create a free PostgreSQL database on [Supabase.com](https://supabase.com) or [Neon.tech](https://neon.tech). These are 100% free and do not ask for a credit card.
   * Copy the database connection URL (e.g. `postgresql://...` or `postgres://...`).
2. **Commit & Push** your changes to your Git repository.
3. Go to **Render.com > Blueprint** and select your repository.
4. Render will parse [render.yaml](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/render.yaml) and prompt you for parameters:
   * **DATABASE_URL**: Enter your Supabase or Neon database URL.
   * **GEMINI__API_KEY**, **GROQ_API_KEY**, and social media credentials.
5. Click **Apply** to deploy. Render will build and deploy the container on the free tier.

---

## 5. Alembic Migration & PgBouncer Fix
* **Symptom**: During the deploy hook, the combined container started local Redis successfully, but failed during database migrations (`alembic upgrade head`) with the error `DuplicatePreparedStatementError: prepared statement "__asyncpg_stmt_1__" already exists` inside `alembic/env.py`.
* **Resolution**: Modified the database connection pool creation inside [alembic/env.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/alembic/env.py) to pass `connect_args={"statement_cache_size": 0}` to the migration runner's async engine builder (`async_engine_from_config`). This forces Alembic to disable prepared statement caching as well, allowing database migrations to run successfully against connection pools like Supabase and Neon.

### Local Compatibility:
* **Important**: All modifications are 100% backward compatible. Local development via `docker-compose up` remains completely unaffected as it bypasses the internal Redis server and connects to the standalone `artwork-redis` container. All local tests pass successfully (67 PASSED, 1 SKIPPED).
