# Integration Walkthrough: Auto Publishing Pipeline (Instagram & YouTube Shorts)

This document walks through the complete implementation of the publishing integrations in the AI Artwork Automation pipeline.

---

## Completed Implementations

### 1. Database Schema Updates
We added columns to the `Artwork` model in [artwork.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/models/artwork.py) to persist publishing states for both platforms:
- **Instagram Tracking**:
  - `instagram_status` (`pending`, `processing`, `published`, `failed`)
  - `instagram_post_id` (Unique Instagram Media Container ID)
  - `instagram_permalink` (Direct view URL of the published post)
  - `instagram_published_at` (Timestamp of publication)
- **YouTube Shorts Tracking**:
  - `youtube_status` (`pending`, `processing`, `published`, `failed`)
  - `youtube_video_id` (YouTube Video ID)
  - `youtube_url` (Public Shorts URL: `https://youtube.com/shorts/{video_id}`)
  - `youtube_published_at` (Timestamp of publication)

These schema modifications were migrated via Alembic (`61cbc473be4c` and `a76ba7fe1bc9` respectively) and applied directly to the PostgreSQL database.

---

### 2. Service Integrations

#### A. Instagram Publisher Service
Created [instagram_publisher.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/services/instagram_publisher.py):
- Orchestrates Meta Graph API calls:
  1. Initialize Media Container (`POST /v19.0/{account_id}/media`)
  2. Poll Container Status (`GET /v19.0/{container_id}`) with 5-second interval retries
  3. Publish Media Reel (`POST /v19.0/{account_id}/media_publish`)
  4. Fetch Permalink (`GET /v19.0/{post_id}?fields=permalink`)

#### B. YouTube Publisher Service
Created [youtube_publisher.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/services/youtube_publisher.py):
- Orchestrates Google OAuth & Resumable Video Upload:
  1. Retrieve Access Token via OAuth token refresh endpoint (`https://oauth2.googleapis.com/token`)
  2. Initiate Resumable Upload Session by posting metadata (`https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status`) and parsing the returned `Location` header
  3. Upload raw MP4 video bytes via a `PUT` request to the returned upload session URL
  4. Automatically appends `#shorts` to titles and restricts them to the 100-character limit

---

### 3. API Router & Schemas
Defined request/response models in [artwork.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/schemas/artwork.py). Added the following endpoints in [artwork.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/api/v1/artwork.py) along with their corresponding dependencies in [deps.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/api/deps.py):
- `POST /api/v1/artworks/{id}/publish/instagram` & `GET /api/v1/artworks/{id}/instagram-status`
- `POST /api/v1/artworks/{id}/publish/youtube` & `GET /api/v1/artworks/{id}/youtube-status`

---

### 4. LangGraph Workflow Routing & Nodes
- Replaced the mock publishing nodes in [nodes.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/graph/nodes.py) with the real service-calling integrations.
- Configured structured telemetry logs: `instagram_publish_started`, `instagram_publish_completed`, `instagram_publish_failed`, `youtube_publish_started`, `youtube_publish_completed`, and `youtube_publish_failed`.
- Redefined conditional transitions in [workflow.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/graph/workflow.py) to achieve the requested execution chain:
  `generate_reel` -> `publish_instagram` -> `publish_youtube` -> `collect_analytics`.
- The graph checks flag statuses in the settings:
  - If a step is disabled, it is gracefully bypassed to the next active publishing step.
  - If any publishing node fails, it transitions directly to the `handle_error` node.

---

## Verification Results

### 1. Database Migrations
Both Alembic migrations successfully completed upgrades inside PostgreSQL:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade e04218e7bbac -> 61cbc473be4c, add_instagram_publishing_fields
INFO  [alembic.runtime.migration] Running upgrade 61cbc473be4c -> a76ba7fe1bc9, add_youtube_publishing_fields
```

### 2. Test Execution (27/27 Passing)
Running the entire test suite on the host confirms all unit and integration tests (including OAuth token fetches, resumable bytes upload, API endpoints, and workflow node state transitions) pass cleanly:
```
platform win32 -- Python 3.11.2, pytest-9.0.3, pluggy-1.6.0
plugins: anyio-4.13.0, Faker-40.21.0, langsmith-0.8.8, asyncio-1.4.0, cov-7.1.0
collected 27 items

tests/integration/test_artwork_workflow.py::test_upload_artwork_api PASSED
tests/integration/test_artwork_workflow.py::test_trigger_workflow_api PASSED
tests/integration/test_artwork_workflow.py::test_get_analysis_api PASSED
tests/integration/test_artwork_workflow.py::test_get_seo_api PASSED
tests/integration/test_artwork_workflow.py::test_get_caption_api PASSED
tests/integration/test_artwork_workflow.py::test_get_hashtags_api PASSED
tests/integration/test_artwork_workflow.py::test_get_reel_api PASSED
tests/test_instagram_publish.py::test_instagram_publisher_service_success PASSED
tests/test_instagram_publish.py::test_publish_instagram_api_endpoints PASSED
tests/test_instagram_publish.py::test_publish_instagram_graph_node PASSED
tests/test_youtube_publish.py::test_youtube_publisher_service_success PASSED
tests/test_youtube_publish.py::test_youtube_publisher_service_missing_credentials PASSED
tests/test_youtube_publish.py::test_youtube_publisher_service_token_failure PASSED
tests/test_youtube_publish.py::test_publish_youtube_api_endpoints PASSED
tests/test_youtube_publish.py::test_publish_youtube_graph_node PASSED
unit tests PASSED (12 items)
======================== 27 passed, 1 warning in 4.35s ========================
```
