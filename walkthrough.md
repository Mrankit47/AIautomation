# Walkthrough: Hybrid AI Provider Architecture & Resiliency Suite

This document walks through the integration of the Hybrid AI Provider Architecture and workflow resiliency features designed to eliminate Gemini rate limit failures by routing text generation tasks to Groq while keeping Gemini for image understanding.

---

## Changes Completed

### 1. Configuration & Settings
* Updated [settings.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/config/settings.py) to support:
  * `ai_provider`: Runtime selector (`"gemini"` or `"groq"`).
  * `groq_api_key`: Secret API key for Groq Cloud.
  * `groq_model`: Model name defaulting to `llama-3.3-70b-versatile`.

### 2. Provider Abstraction & Factory
* **Groq Provider** ([groq.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/providers/groq.py)):
  * Implements `AIProvider` using the official `AsyncGroq` client.
  * Employs exponential backoff retry logic (up to 3 retries) on transient API exceptions.
  * Implements structured JSON mode for schema enforcement.
* **Provider Factory** ([factory.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/providers/factory.py)):
  * Provides `get_provider(provider_name)` to dynamically resolve the required provider instance.

### 3. Database Status Mappings (No-Schema Hack)
* To support the new `completed_with_warnings` status without altering PostgreSQL native enums, we implemented SQLAlchemy `hybrid_property` mappings:
  * **Workflow Run** ([workflow_run.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/models/workflow_run.py)) and **Artwork** ([artwork.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/models/artwork.py)) store status in `_db_status` column.
  * Getter returns `completed_with_warnings` if there are elements in `error_history` and `_db_status == completed`.
  * Setter transparently maps `completed_with_warnings` back to `completed` for database persistence.

### 4. Agent & Service Migrations
* Migrated [MetadataGeneratorAgent](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/agents/metadata_generator.py), [SEOAgent](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/agents/seo_agent.py), [CaptionAgent](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/agents/caption_agent.py), [HashtagAgent](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/agents/hashtag_agent.py), and [ReelScriptAgent](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/agents/reel_script_agent.py) to resolve dependencies using `get_provider()`.
* Migrated [AIRecommendationService](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/services/ai_recommendations.py) to use `get_provider()`.

### 5. API Endpoints & Events
* Created system router endpoint `GET /api/v1/system/providers` in [system.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/api/v1/system.py) to return provider health diagnostics.
* Mounted router in [router.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/api/router.py).
* Integrated startup checks in [events.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/core/events.py) to validate keys and log default provider details on startup.

### 6. Workflow Resiliency Nodes
* Modified `generate_caption`, `generate_hashtags`, and `generate_reel` nodes in [nodes.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/graph/nodes.py):
  * Exceptions are caught as warnings, logged to `error_history`, and the workflow runs continue.
  * Transitions update the workflow status to `completed_with_warnings` at the end of execution.
* Modified [workflow_task.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/tasks/workflow_task.py) to complete celery tasks with warnings without crashing.

---

## Verification Results

### 1. Pytest Suite (54/54 Passing)
All tests pass successfully on the host:
```bash
tests/test_groq_provider.py PASSED
tests/test_provider_factory.py PASSED
tests/test_caption_agent_groq.py PASSED
tests/test_hashtag_agent_groq.py PASSED
tests/test_reel_script_agent_groq.py PASSED
tests/test_system_providers_api.py PASSED
tests/test_workflow_warnings.py PASSED
...
======================= 54 passed, 2 warnings in 4.17s ========================
```

### 2. Manual System Health Check
Running inside Docker container returns valid HTTP 200:
```json
{"gemini":"healthy","groq":"unhealthy","default_provider":"gemini"}
```
*(Groq is marked `unhealthy` if no `GROQ_API_KEY` is present in the `.env` file).*
