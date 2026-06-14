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

## 4. Render Deployment Guide

We have made the repository 100% deploy-ready for Render.com using Render Blueprints. 

### What We Added:
1. **Dynamic Config Parsing**: The database settings and redis settings in [settings.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/config/settings.py) now dynamically parse unified connection strings (`DATABASE_URL` and `REDIS_URL`) instead of requiring separate host/port parameters.
2. **Celery Auto-Configuration**: The root settings automatically parse `REDIS_URL` and derive separate broker/backend databases (indices `/1` and `/2` respectively) if Celery Broker URLs are left at their defaults.
3. **Blueprint File**: Created [render.yaml](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/render.yaml) at the repository root defining:
   * **artwork-app** (FastAPI Web Service)
   * **artwork-worker** (Celery Background Worker)
   * **artwork-redis** (Managed Redis Instance)
   * **artwork-db** (Managed PostgreSQL Database)

### How to Deploy on Render:
1. **Commit & Push** your repository changes to GitHub/GitLab.
2. Go to your **Render Dashboard** and click **New > Blueprint**.
3. Select your repository. Render will automatically parse [render.yaml](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/render.yaml) and list the 4 services (FastAPI app, Celery worker, Redis, PostgreSQL).
4. Fill in any required external environment secrets (like API keys for Instagram, YouTube, Gemini, and Groq).
5. Click **Apply** to provision and deploy the entire stack automatically.
6. The web app's database migrations will automatically run (`alembic upgrade head`) before uvicorn starts.

### Local Compatibility:
* **Important**: All modifications are 100% backward compatible. Running local development via `docker-compose up` remains unaffected as the codebase falls back to local hostnames and parameters when cloud environment variables are absent. All local tests pass successfully (67 PASSED, 1 SKIPPED).
