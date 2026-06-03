# AI Artwork Publishing Automation Platform — Implementation Plan v2

## Goal

Build a production-grade project foundation and architecture for an AI Artwork Publishing Automation Platform. This phase creates only the scalable skeleton — no AI prompts, no video generation, no social media publishing logic.

### Full Future Pipeline

```
Artwork Upload → Artwork Analysis → Metadata Generation → SEO Generation
→ Caption Generation → Hashtag Generation → Reel/Short Video Generation
→ Instagram Publishing → YouTube Shorts Publishing → Pinterest Publishing
→ Analytics Collection → Performance Reporting
```

### This Phase Scope

Architecture and foundation only. No business logic.

## Project Root

```
c:\Users\Ankit\OneDrive\Desktop\All Projects\AIautomation\
```

---

## Complete File Tree

```
AIautomation/
├── backend/
│   ├── __init__.py
│   ├── main.py                                  # FastAPI app entrypoint
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py                            # Top-level API router aggregator
│   │   ├── deps.py                              # Dependency injection providers
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── health.py                        # Health-check endpoints
│   │       ├── artwork.py                       # Artwork upload & status endpoints
│   │       └── auth.py                          # Auth endpoints (login, refresh)
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt.py                               # JWT token creation & verification
│   │   ├── dependencies.py                      # Auth dependency injectors (get_current_user)
│   │   ├── schemas.py                           # Auth request/response schemas
│   │   └── service.py                           # Auth business logic
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                              # Abstract base agent interface
│   │   ├── artwork_analyzer.py                  # Artwork analysis agent stub
│   │   ├── metadata_generator.py                # Metadata generation agent stub
│   │   └── content_generator.py                 # SEO / caption / hashtag agent stub
│   │
│   ├── crews/
│   │   ├── __init__.py
│   │   ├── base.py                              # Abstract base crew interface
│   │   └── artwork_crew.py                      # Artwork processing crew stub
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py                             # LangGraph state definition (upgraded)
│   │   ├── nodes.py                             # Graph node functions
│   │   └── workflow.py                          # LangGraph workflow builder
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── artwork_service.py                   # Artwork business logic
│   │   └── workflow_service.py                  # Workflow orchestration service
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                              # SQLAlchemy declarative base & mixins
│   │   ├── artwork.py                           # Artwork ORM model
│   │   ├── workflow_run.py                      # Workflow run ORM model
│   │   └── user.py                              # User ORM model (for JWT auth)
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── artwork.py                           # Pydantic schemas for artwork
│   │   ├── workflow.py                          # Pydantic schemas for workflow
│   │   └── health.py                            # Health-check response schemas
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py                        # Custom exception hierarchy
│   │   ├── middleware.py                        # Error handling & request logging middleware
│   │   ├── events.py                            # App startup / shutdown lifecycle events
│   │   └── logging.py                           # structlog configuration
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py                          # Pydantic Settings (env-based config)
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py                              # Abstract storage interface
│   │   └── local.py                             # Local filesystem storage implementation
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── session.py                           # Async SQLAlchemy engine & session factory
│   │   └── repository.py                        # Generic async repository base class
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py                        # Celery application factory
│   │   ├── base_task.py                         # Abstract base task with retry/logging
│   │   ├── artwork_task.py                      # Artwork processing Celery task
│   │   └── workflow_task.py                     # Workflow orchestration Celery task
│   │
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py                              # Abstract AI provider interface
│   │   └── gemini.py                            # Gemini API integration stub
│   │
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── base.py                              # Abstract integration interface
│   │   ├── instagram/
│   │   │   ├── __init__.py
│   │   │   ├── client.py                        # Instagram Graph API client stub
│   │   │   ├── schemas.py                       # Instagram data schemas
│   │   │   └── exceptions.py                    # Instagram-specific exceptions
│   │   ├── youtube/
│   │   │   ├── __init__.py
│   │   │   ├── client.py                        # YouTube Data API client stub
│   │   │   ├── schemas.py                       # YouTube data schemas
│   │   │   └── exceptions.py                    # YouTube-specific exceptions
│   │   ├── pinterest/
│   │   │   ├── __init__.py
│   │   │   ├── client.py                        # Pinterest API client stub
│   │   │   ├── schemas.py                       # Pinterest data schemas
│   │   │   └── exceptions.py                    # Pinterest-specific exceptions
│   │   └── cloudinary/
│   │       ├── __init__.py
│   │       ├── client.py                        # Cloudinary upload/transform client stub
│   │       ├── schemas.py                       # Cloudinary data schemas
│   │       └── exceptions.py                    # Cloudinary-specific exceptions
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── base.py                              # Prompt template engine & versioning
│   │   ├── registry.py                          # Prompt registry (load/resolve by name+version)
│   │   ├── artwork_analysis/
│   │   │   ├── __init__.py
│   │   │   └── v1.yaml                          # Artwork analysis prompt template v1
│   │   ├── seo/
│   │   │   ├── __init__.py
│   │   │   └── v1.yaml                          # SEO prompt template v1
│   │   ├── captions/
│   │   │   ├── __init__.py
│   │   │   └── v1.yaml                          # Caption prompt template v1
│   │   └── hashtags/
│   │       ├── __init__.py
│   │       └── v1.yaml                          # Hashtag prompt template v1
│   │
│   ├── media/
│   │   ├── __init__.py
│   │   ├── base.py                              # Abstract media processor interface
│   │   ├── reel_templates/
│   │   │   ├── __init__.py
│   │   │   └── .gitkeep
│   │   ├── fonts/
│   │   │   └── .gitkeep
│   │   └── music/
│   │       └── .gitkeep
│   │
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── base.py                              # Abstract analytics interfaces
│   │   ├── collectors/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                          # Abstract collector interface
│   │   │   ├── instagram_collector.py           # Instagram analytics collector stub
│   │   │   ├── youtube_collector.py             # YouTube analytics collector stub
│   │   │   └── pinterest_collector.py           # Pinterest analytics collector stub
│   │   └── reports/
│   │       ├── __init__.py
│   │       ├── base.py                          # Abstract report generator interface
│   │       └── performance_report.py            # Performance report generator stub
│   │
│   └── workers/
│       ├── __init__.py
│       └── celery_worker.py                     # Celery worker entry point
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                              # Shared fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_health.py                       # Health endpoint tests
│   │   ├── test_artwork_service.py              # Artwork service tests
│   │   ├── test_jwt.py                          # JWT utility tests
│   │   └── test_prompt_registry.py              # Prompt registry tests
│   └── integration/
│       ├── __init__.py
│       └── test_artwork_workflow.py             # End-to-end workflow test
│
├── docker/
│   ├── Dockerfile                               # Multi-stage production Dockerfile
│   └── Dockerfile.dev                           # Development Dockerfile
│
├── scripts/
│   ├── start.sh                                 # Production start script
│   ├── dev.sh                                   # Development start script
│   └── start_celery.sh                          # Celery worker start script
│
├── logs/
│   └── .gitkeep
│
├── outputs/
│   └── .gitkeep
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── .gitkeep
│
├── alembic.ini
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

**Total: ~100 files** across 30+ directories.

---

## Proposed Changes

### 1. Project Configuration

#### [NEW] pyproject.toml
- Project metadata, Python 3.11 requirement
- Ruff config (line-length 100, select rules: E, W, F, I, N, UP, ANN, B, SIM)
- Black config (line-length 100)
- Mypy config (strict mode, SQLAlchemy + Pydantic plugins)
- Pytest config (asyncio_mode = "auto", testpaths = ["tests"])

#### [NEW] requirements.txt
```
# Core
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
pydantic>=2.10.0
pydantic-settings>=2.7.0

# Database
sqlalchemy[asyncio]>=2.0.36
asyncpg>=0.30.0
alembic>=1.14.0

# Redis & Task Queue
redis[hiredis]>=5.2.0
celery[redis]>=5.4.0

# AI Orchestration
langgraph>=0.2.0
crewai>=0.86.0

# AI Provider
google-generativeai>=0.8.0

# Auth
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# Storage & Files
aiofiles>=24.1.0
python-multipart>=0.0.18

# Logging
structlog>=24.4.0

# Utilities
python-dotenv>=1.0.1
httpx>=0.28.0
pyyaml>=6.0.2
jinja2>=3.1.4
```

#### [NEW] requirements-dev.txt
```
-r requirements.txt
pytest>=8.3.0
pytest-asyncio>=0.24.0
pytest-cov>=6.0.0
httpx>=0.28.0
ruff>=0.8.0
black>=24.10.0
mypy>=1.13.0
types-aiofiles
types-redis
types-pyyaml
types-passlib
types-python-jose
factory-boy>=3.3.0
```

#### [NEW] .env.example
```bash
# ── Application ──────────────────────────────────────
APP_NAME=artwork-automation
APP_ENV=development
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000
APP_LOG_LEVEL=DEBUG
APP_CORS_ORIGINS=["http://localhost:3000"]

# ── PostgreSQL ───────────────────────────────────────
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=artwork_user
POSTGRES_PASSWORD=artwork_secret
POSTGRES_DB=artwork_automation
DATABASE_URL=postgresql+asyncpg://artwork_user:artwork_secret@localhost:5432/artwork_automation

# ── Redis ────────────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_URL=redis://localhost:6379/0

# ── Celery ───────────────────────────────────────────
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ── JWT Authentication ───────────────────────────────
JWT_SECRET_KEY=CHANGE-ME-TO-RANDOM-64-CHAR-SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ── Gemini AI ────────────────────────────────────────
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MAX_RETRIES=3
GEMINI_TIMEOUT=60

# ── Cloudinary ───────────────────────────────────────
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
CLOUDINARY_UPLOAD_PRESET=

# ── Instagram ────────────────────────────────────────
INSTAGRAM_APP_ID=
INSTAGRAM_APP_SECRET=
INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_BUSINESS_ACCOUNT_ID=

# ── YouTube ──────────────────────────────────────────
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=
YOUTUBE_CHANNEL_ID=

# ── Pinterest ────────────────────────────────────────
PINTEREST_APP_ID=
PINTEREST_APP_SECRET=
PINTEREST_ACCESS_TOKEN=
PINTEREST_BOARD_ID=

# ── Storage ──────────────────────────────────────────
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=./outputs

# ── Prompts ──────────────────────────────────────────
PROMPTS_DIR=backend/prompts
PROMPTS_DEFAULT_VERSION=v1
```

#### [NEW] .gitignore
- Standard Python ignores, .env, logs/, outputs/, __pycache__, .mypy_cache, .pytest_cache, .ruff_cache, *.egg-info, dist/, build/, .venv/

---

### 2. Configuration & Core

#### [NEW] [settings.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/config/settings.py)

`Settings` class via `pydantic_settings.BaseSettings` with **nested config models**:

```python
class DatabaseSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    user: str = "artwork_user"
    password: SecretStr = SecretStr("artwork_secret")
    name: str = "artwork_automation"
    url: str | None = None  # Override, or built from parts
    pool_size: int = 20
    max_overflow: int = 10

class RedisSettings(BaseModel): ...
class CelerySettings(BaseModel): ...
class JWTSettings(BaseModel): ...
class GeminiSettings(BaseModel): ...
class CloudinarySettings(BaseModel): ...
class InstagramSettings(BaseModel): ...
class YouTubeSettings(BaseModel): ...
class PinterestSettings(BaseModel): ...
class StorageSettings(BaseModel): ...
class PromptSettings(BaseModel): ...

class Settings(BaseSettings):
    app_name: str = "artwork-automation"
    app_env: str = "development"  # development | staging | production
    app_debug: bool = False
    # ... nested settings for each subsystem
```

Singleton accessor: `get_settings() -> Settings` with `@lru_cache`.

#### [NEW] [exceptions.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/core/exceptions.py)

```
AppException (base)
├── NotFoundException (404)
├── ValidationException (422)
├── AuthenticationException (401)
├── AuthorizationException (403)
├── StorageException (500)
├── AIProviderException (502)
├── WorkflowException (500)
├── IntegrationException (502)
├── RateLimitException (429)
└── TaskException (500)
```

Each carries: `status_code`, `error_code` (string enum), `detail`, optional `context` dict.

#### [NEW] [middleware.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/core/middleware.py)

- **`ErrorHandlingMiddleware`** — catches `AppException` subtypes and unhandled exceptions, returns structured JSON `{"error_code": ..., "detail": ..., "correlation_id": ...}`, logs with correlation IDs
- **`RequestLoggingMiddleware`** — logs method, path, status, duration, binds `correlation_id` and `request_id` to structlog context
- **`CorrelationIdMiddleware`** — extracts or generates `X-Correlation-ID` header, injects into structlog context

#### [NEW] [events.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/core/events.py)

`lifespan` async context manager:
- **Startup**: init DB engine pool, init Redis connection pool, configure structlog, validate critical settings
- **Shutdown**: dispose DB engine, close Redis pool, flush logs

#### [NEW] [logging.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/core/logging.py)

Production-grade structlog configuration:

```python
def setup_logging(log_level: str = "INFO", json_format: bool = True) -> None:
    """Configure structlog with JSON output, correlation IDs, and processors."""
```

Processors chain:
1. `structlog.contextvars.merge_contextvars` — merges `correlation_id`, `workflow_id`, `request_id`
2. `structlog.processors.add_log_level`
3. `structlog.processors.TimeStamper(fmt="iso")`
4. `structlog.processors.StackInfoRenderer()`
5. `structlog.processors.ExceptionRenderer()`
6. `structlog.processors.JSONRenderer()` (prod) or `structlog.dev.ConsoleRenderer()` (dev)

Context variable bindings supported:
- `correlation_id` — tracks a request across services
- `workflow_id` — tracks a specific workflow run
- `request_id` — unique per HTTP request
- `artwork_id` — current artwork being processed
- `task_id` — Celery task ID

---

### 3. Database & Models

#### [NEW] [session.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/database/session.py)
- `create_async_engine` with pool_size, max_overflow from settings
- `async_sessionmaker` factory
- `get_db_session()` async generator for FastAPI DI

#### [NEW] [repository.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/database/repository.py)
- Generic `BaseRepository[ModelType]` with async CRUD
- Methods: `get_by_id`, `get_all`, `create`, `update`, `delete`, `filter_by`, `count`, `exists`
- Pagination support via `get_paginated(page, per_page)`

#### [NEW] [base.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/models/base.py) (models)
- `Base` = `DeclarativeBase`
- `TimestampMixin`: `created_at`, `updated_at` (auto-set)
- `UUIDMixin`: UUID4 primary key

#### [NEW] [artwork.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/models/artwork.py)
- `ArtworkStatus` enum: `uploaded`, `analyzing`, `processing`, `publishing`, `completed`, `failed`
- `Artwork` model: id, title, original_filename, file_path, storage_url, file_size, mime_type, width, height, status, analysis_data (JSON), metadata (JSON), seo_data (JSON), caption, hashtags (JSON array), reel_path, error_message, timestamps
- Relationship to `WorkflowRun`

#### [NEW] [workflow_run.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/models/workflow_run.py)
- `WorkflowStatus` enum: `pending`, `running`, `completed`, `failed`, `cancelled`
- `WorkflowRun` model: id, artwork_id (FK), workflow_version, status, current_node, started_at, completed_at, result (JSON), error_history (JSON array), instagram_status, youtube_status, pinterest_status, celery_task_id

#### [NEW] [user.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/models/user.py)
- `User` model: id, email (unique), hashed_password, full_name, is_active, is_superuser, last_login, timestamps

#### [NEW] Alembic configuration
- `alembic.ini` with async driver
- `alembic/env.py` configured for async migrations, imports all models

---

### 4. JWT Authentication (`backend/auth/`)

#### [NEW] [jwt.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/auth/jwt.py)
```python
class JWTHandler:
    """Handles JWT token creation, verification, and refresh."""

    def create_access_token(self, subject: str, extra_claims: dict | None = None) -> str: ...
    def create_refresh_token(self, subject: str) -> str: ...
    def decode_token(self, token: str) -> TokenPayload: ...
```
- Uses `python-jose` with HS256
- Configurable expiry from settings
- `TokenPayload` Pydantic model for decoded claims

#### [NEW] [dependencies.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/auth/dependencies.py)
```python
async def get_current_user(token: str = Depends(oauth2_scheme), ...) -> User: ...
async def get_current_active_user(user: User = Depends(get_current_user)) -> User: ...
async def require_superuser(user: User = Depends(get_current_active_user)) -> User: ...
```
- `OAuth2PasswordBearer` scheme pointing to `/api/v1/auth/login`

#### [NEW] [schemas.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/auth/schemas.py)
- `LoginRequest`, `TokenResponse`, `TokenPayload`, `RefreshRequest`, `UserCreate`, `UserResponse`

#### [NEW] [service.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/auth/service.py)
- `AuthService`: `authenticate_user`, `create_user`, `refresh_tokens`
- Password hashing via `passlib[bcrypt]`

---

### 5. Celery Task Processing (`backend/tasks/`)

> [!IMPORTANT]
> Replaces the previous `backend/workers/` approach with FastAPI BackgroundTasks. The `workers/` directory now only contains the Celery worker entry point.

#### [NEW] [celery_app.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/tasks/celery_app.py)
```python
from celery import Celery

def create_celery_app() -> Celery:
    """Factory for Celery application with Redis broker & backend."""
    app = Celery("artwork_automation")
    app.config_from_object({
        "broker_url": settings.celery.broker_url,
        "result_backend": settings.celery.result_backend,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "task_track_started": True,
        "task_acks_late": True,
        "worker_prefetch_multiplier": 1,
        "task_routes": {
            "backend.tasks.artwork_task.*": {"queue": "artwork"},
            "backend.tasks.workflow_task.*": {"queue": "workflow"},
        },
    })
    app.autodiscover_tasks(["backend.tasks"])
    return app

celery_app = create_celery_app()
```

#### [NEW] [base_task.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/tasks/base_task.py)
```python
class BaseTask(celery.Task):
    """Abstract base task with structured logging, retry policy, and error tracking."""
    abstract = True
    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 600

    def before_start(self, task_id, args, kwargs): ...  # bind task_id to structlog
    def on_failure(self, exc, task_id, args, kwargs, einfo): ...  # log + store error
    def on_success(self, retval, task_id, args, kwargs): ...  # log completion
```

#### [NEW] [artwork_task.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/tasks/artwork_task.py)
- `process_artwork(artwork_id: str)` — Celery task stub
- Binds `artwork_id` and `workflow_id` to structlog context

#### [NEW] [workflow_task.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/tasks/workflow_task.py)
- `execute_workflow(artwork_id: str, workflow_version: str)` — Celery task stub
- Will invoke LangGraph workflow in future phases

#### [NEW] [celery_worker.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/workers/celery_worker.py)
- Worker entry point that imports `celery_app` and configures logging

---

### 6. Integrations Layer (`backend/integrations/`)

#### [NEW] [base.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/integrations/base.py)
```python
class SocialMediaClient(ABC):
    """Abstract interface for social media platform clients."""

    @abstractmethod
    async def authenticate(self) -> None: ...

    @abstractmethod
    async def publish_image(self, image_path: str, caption: str, **kwargs) -> PublishResult: ...

    @abstractmethod
    async def publish_video(self, video_path: str, title: str, **kwargs) -> PublishResult: ...

    @abstractmethod
    async def get_post_analytics(self, post_id: str) -> PostAnalytics: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

class MediaStorageClient(ABC):
    """Abstract interface for cloud media storage/CDN clients."""

    @abstractmethod
    async def upload(self, file_path: str, **kwargs) -> UploadResult: ...

    @abstractmethod
    async def transform(self, public_id: str, transformations: dict) -> str: ...

    @abstractmethod
    async def delete(self, public_id: str) -> None: ...

@dataclass
class PublishResult:
    post_id: str
    url: str
    platform: str
    published_at: datetime
    raw_response: dict

@dataclass
class PostAnalytics:
    post_id: str
    impressions: int
    reach: int
    likes: int
    comments: int
    shares: int
    saves: int
    collected_at: datetime

@dataclass
class UploadResult:
    public_id: str
    url: str
    secure_url: str
    format: str
    bytes: int
```

#### Instagram (`backend/integrations/instagram/`)

| File | Contents |
|------|----------|
| `client.py` | `InstagramClient(SocialMediaClient)` — stub with Instagram Graph API URL constants, `publish_image`, `publish_video`, `get_post_analytics` |
| `schemas.py` | `InstagramPost`, `InstagramMediaResponse`, `InstagramInsights` |
| `exceptions.py` | `InstagramAPIError`, `InstagramRateLimitError`, `InstagramAuthError` |

#### YouTube (`backend/integrations/youtube/`)

| File | Contents |
|------|----------|
| `client.py` | `YouTubeClient(SocialMediaClient)` — stub with YouTube Data API v3 URL constants |
| `schemas.py` | `YouTubeVideo`, `YouTubeUploadResponse`, `YouTubeAnalytics` |
| `exceptions.py` | `YouTubeAPIError`, `YouTubeQuotaExceededError`, `YouTubeAuthError` |

#### Pinterest (`backend/integrations/pinterest/`)

| File | Contents |
|------|----------|
| `client.py` | `PinterestClient(SocialMediaClient)` — stub with Pinterest API v5 URL constants |
| `schemas.py` | `PinterestPin`, `PinterestBoardResponse`, `PinterestAnalytics` |
| `exceptions.py` | `PinterestAPIError`, `PinterestRateLimitError`, `PinterestAuthError` |

#### Cloudinary (`backend/integrations/cloudinary/`)

| File | Contents |
|------|----------|
| `client.py` | `CloudinaryClient(MediaStorageClient)` — stub with upload/transform/delete |
| `schemas.py` | `CloudinaryUploadResponse`, `CloudinaryTransformation` |
| `exceptions.py` | `CloudinaryAPIError`, `CloudinaryUploadError` |

---

### 7. Prompt Management Layer (`backend/prompts/`)

#### [NEW] [base.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/prompts/base.py)
```python
@dataclass
class PromptTemplate:
    """Versioned prompt template loaded from YAML."""
    name: str
    version: str
    system_prompt: str
    user_prompt_template: str  # Jinja2 template string
    output_schema: dict | None  # JSON schema for structured output
    metadata: dict

    def render(self, **kwargs: Any) -> str:
        """Render user prompt with Jinja2 variables."""
```

#### [NEW] [registry.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/prompts/registry.py)
```python
class PromptRegistry:
    """Discovers, loads, and caches prompt templates from the filesystem."""

    def __init__(self, prompts_dir: str, default_version: str = "v1") -> None: ...

    def get(self, category: str, name: str | None = None, version: str | None = None) -> PromptTemplate: ...
    def list_versions(self, category: str) -> list[str]: ...
    def reload(self) -> None:
        """Hot-reload prompts from disk without restart."""
```

#### YAML prompt template format (example `artwork_analysis/v1.yaml`):
```yaml
name: artwork_analysis
version: v1
description: Analyze an artwork image for style, medium, mood, and subject.
system_prompt: |
  You are an expert art analyst. Analyze the provided artwork image.
  # ... (placeholder — actual prompt text deferred to future phase)
user_prompt_template: |
  Analyze this artwork: {{ artwork_title }}
  Additional context: {{ context | default('None') }}
output_schema:
  type: object
  properties:
    style:
      type: string
    medium:
      type: string
    mood:
      type: string
    subjects:
      type: array
      items:
        type: string
metadata:
  author: system
  created_at: "2025-01-01"
```

---

### 8. Media Layer (`backend/media/`)

#### [NEW] [base.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/media/base.py)
```python
class MediaProcessor(ABC):
    """Abstract interface for media processing (images, reels, shorts)."""

    @abstractmethod
    async def create_reel(
        self,
        image_path: str,
        template_name: str,
        music_path: str | None = None,
        duration: int = 15,
        **kwargs: Any,
    ) -> MediaResult: ...

    @abstractmethod
    async def resize_image(
        self,
        image_path: str,
        width: int,
        height: int,
        format: str = "webp",
    ) -> str: ...

    @abstractmethod
    async def get_image_metadata(self, image_path: str) -> ImageMetadata: ...

@dataclass
class MediaResult:
    output_path: str
    format: str
    duration: float | None
    file_size: int

@dataclass
class ImageMetadata:
    width: int
    height: int
    format: str
    color_space: str
    file_size: int
    dominant_colors: list[str]
```

Asset directories created with `.gitkeep`:
- `reel_templates/` — future reel/short template files
- `fonts/` — typography assets for video overlay
- `music/` — background music for reels

---

### 9. Analytics Layer (`backend/analytics/`)

#### [NEW] [base.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/analytics/base.py)
```python
class AnalyticsCollector(ABC):
    """Abstract interface for platform analytics collection."""
    platform: str

    @abstractmethod
    async def collect_post_metrics(self, post_id: str) -> PostMetrics: ...

    @abstractmethod
    async def collect_account_metrics(self) -> AccountMetrics: ...

    @abstractmethod
    async def collect_period_metrics(self, start: datetime, end: datetime) -> PeriodMetrics: ...

class ReportGenerator(ABC):
    """Abstract interface for analytics report generation."""

    @abstractmethod
    async def generate(self, artwork_id: str, period: str = "7d") -> Report: ...

    @abstractmethod
    async def generate_comparison(self, artwork_ids: list[str]) -> ComparisonReport: ...
```

#### Collectors (`backend/analytics/collectors/`)

| File | Class | Purpose |
|------|-------|---------|
| `base.py` | Re-exports `AnalyticsCollector` | Common collector utilities |
| `instagram_collector.py` | `InstagramAnalyticsCollector(AnalyticsCollector)` | Stub — calls `InstagramClient.get_post_analytics` |
| `youtube_collector.py` | `YouTubeAnalyticsCollector(AnalyticsCollector)` | Stub — calls `YouTubeClient.get_post_analytics` |
| `pinterest_collector.py` | `PinterestAnalyticsCollector(AnalyticsCollector)` | Stub — calls `PinterestClient.get_post_analytics` |

#### Reports (`backend/analytics/reports/`)

| File | Class | Purpose |
|------|-------|---------|
| `base.py` | Re-exports `ReportGenerator` | Common report utilities |
| `performance_report.py` | `PerformanceReportGenerator(ReportGenerator)` | Aggregates cross-platform metrics |

---

### 10. Upgraded LangGraph Workflow State (`backend/graph/`)

#### [MODIFIED] [state.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/graph/state.py)

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class WorkflowError(TypedDict):
    node: str
    error_type: str
    message: str
    timestamp: str

class ArtworkWorkflowState(TypedDict):
    """Strongly-typed state for the artwork processing workflow."""

    # ── Identity ─────────────────────────────────────
    artwork_id: str
    workflow_id: str
    workflow_version: str

    # ── Input ────────────────────────────────────────
    image_path: str
    storage_url: str
    original_filename: str

    # ── Analysis ─────────────────────────────────────
    analysis: dict | None           # Raw analysis from AI provider

    # ── Generated Content ────────────────────────────
    metadata: dict | None           # Title, medium, style, etc.
    seo: dict | None                # SEO title, description, keywords
    caption: str | None             # Instagram caption
    hashtags: list[str] | None      # Generated hashtags
    youtube_title: str | None
    youtube_description: str | None

    # ── Media ────────────────────────────────────────
    reel_path: str | None           # Path to generated reel/short

    # ── Publishing Status ────────────────────────────
    instagram_status: str | None    # pending | published | failed
    youtube_status: str | None
    pinterest_status: str | None

    # ── Workflow Control ─────────────────────────────
    workflow_status: str            # pending | running | completed | failed
    current_node: str
    error_history: Annotated[list[WorkflowError], ...]  # Append-only error log
    messages: Annotated[list, add_messages]  # LangGraph message history
```

#### [MODIFIED] [nodes.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/graph/nodes.py)

Expanded node functions matching the full pipeline:

```python
async def analyze_artwork(state: ArtworkWorkflowState) -> dict: ...
async def generate_metadata(state: ArtworkWorkflowState) -> dict: ...
async def generate_seo(state: ArtworkWorkflowState) -> dict: ...
async def generate_caption(state: ArtworkWorkflowState) -> dict: ...
async def generate_hashtags(state: ArtworkWorkflowState) -> dict: ...
async def generate_reel(state: ArtworkWorkflowState) -> dict: ...
async def publish_instagram(state: ArtworkWorkflowState) -> dict: ...
async def publish_youtube(state: ArtworkWorkflowState) -> dict: ...
async def publish_pinterest(state: ArtworkWorkflowState) -> dict: ...
async def collect_analytics(state: ArtworkWorkflowState) -> dict: ...
async def handle_error(state: ArtworkWorkflowState) -> dict: ...
```

All stubs — return state updates with `workflow_status` and `current_node`.

#### [MODIFIED] [workflow.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/graph/workflow.py)

Full pipeline graph:

```
START
  → analyze_artwork
  → generate_metadata
  → generate_seo
  → generate_caption
  → generate_hashtags
  → generate_reel (conditional — skip if disabled)
  → publish_instagram (conditional)
  → publish_youtube (conditional)
  → publish_pinterest (conditional)
  → collect_analytics
  → END

Any node error → handle_error → END
```

Uses `StateGraph` with conditional edges based on `workflow_status`.

---

### 11. Storage, Providers, Agents, Crews

These remain as described in Plan v1, with minor updates:

#### Storage — add `get_public_url()` to interface for CDN support
#### Providers — default model changed to `gemini-2.5-flash`
#### Agents — no changes to interface, stubs remain
#### Crews — no changes to interface, stubs remain

---

### 12. API Layer

#### [NEW] [auth.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/api/v1/auth.py)
- `POST /api/v1/auth/login` — returns JWT access + refresh tokens
- `POST /api/v1/auth/refresh` — refresh access token
- `POST /api/v1/auth/register` — create user (superuser only)

#### [MODIFIED] [artwork.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/api/v1/artwork.py)
- All endpoints now require `Depends(get_current_active_user)`
- `POST /artworks/{id}/process` dispatches Celery task instead of BackgroundTask

#### [MODIFIED] [health.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/api/v1/health.py)
- `GET /health/ready` now also checks Celery worker connectivity

#### [MODIFIED] [deps.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/api/deps.py)
- Added: `get_celery_app`, `get_prompt_registry`, `get_auth_service`

#### [MODIFIED] [router.py](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/backend/api/router.py)
- Includes auth router under `/api/v1/auth`

---

### 13. Docker & Deployment

#### [MODIFIED] [docker-compose.yml](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/docker-compose.yml)

Services: **5 containers**

| Service | Image | Purpose |
|---------|-------|---------|
| `app` | Custom Dockerfile | FastAPI application |
| `celery-worker` | Same image | Celery worker process |
| `postgres` | `postgres:16-alpine` | Database |
| `redis` | `redis:7-alpine` | Cache + Celery broker |
| `celery-flower` | Same image | Celery monitoring (dev only) |

All with health checks, restart policies, named volumes.

#### [NEW] [start_celery.sh](file:///c:/Users/Ankit/OneDrive/Desktop/All%20Projects/AIautomation/scripts/start_celery.sh)
```bash
celery -A backend.tasks.celery_app:celery_app worker \
  --loglevel=info \
  --queues=artwork,workflow \
  --concurrency=4
```

---

### 14. Tests

#### Updated structure:
```
tests/
├── conftest.py                     # Shared fixtures (async client, DB, Redis mock)
├── unit/
│   ├── test_health.py
│   ├── test_artwork_service.py
│   ├── test_jwt.py                 # JWT creation/verification tests
│   └── test_prompt_registry.py     # Prompt loading/versioning tests
└── integration/
    └── test_artwork_workflow.py    # End-to-end workflow test (mocked)
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Celery + Redis** over BackgroundTasks | Distributed task processing, retry policies, monitoring via Flower, horizontal scaling — essential for production video generation and publishing |
| **JWT Authentication** | Stateless auth scales horizontally, supports future dashboard/mobile clients, standard OAuth2 flow |
| **Externalized YAML prompts** | Prompts evolve independently of code; versioning enables A/B testing; non-engineers can edit prompts |
| **Jinja2 for prompt rendering** | Industry standard template engine, supports conditionals/loops/filters for complex prompts |
| **Abstract `SocialMediaClient`** | Adding Facebook, TikTok, or X requires only a new client implementation — zero changes to workflow logic |
| **Abstract `AnalyticsCollector`** | Decouples metric collection from reporting; each platform's API quirks are isolated |
| **`error_history` as append-only list** | Full audit trail of failures across workflow nodes; supports retry analysis and debugging |
| **Separate Celery queues** (`artwork`, `workflow`) | Isolate workloads, enable independent scaling of CPU-heavy (video) vs I/O-heavy (publishing) tasks |
| **structlog with contextvars** | Correlation IDs flow automatically across async boundaries without manual threading |
| **`gemini-2.5-flash`** default | Fast, cost-effective for high-volume artwork processing; easily overridden to `pro` via env var |

---

## Dependency Changes from Plan v1

| Added | Removed | Changed |
|-------|---------|---------|
| `celery[redis]>=5.4.0` | — | — |
| `python-jose[cryptography]>=3.3.0` | — | — |
| `passlib[bcrypt]>=1.7.4` | — | — |
| `pyyaml>=6.0.2` | — | — |
| `jinja2>=3.1.4` | — | — |
| `types-pyyaml` (dev) | — | — |
| `types-passlib` (dev) | — | — |
| `types-python-jose` (dev) | — | — |
| `factory-boy>=3.3.0` (dev) | — | — |
| — | — | Default Gemini model → `gemini-2.5-flash` |

---

## Verification Plan

### Automated Tests
```bash
# Start infrastructure
docker-compose -f docker-compose.dev.yml up -d postgres redis

# Run tests
pytest tests/ -v --tb=short --cov=backend --cov-report=term-missing

# Code quality
ruff check backend/
black --check backend/
mypy backend/
```

### Manual Verification
1. `docker-compose up` — all 5 services start healthy
2. `GET /api/v1/health` → `{"status": "healthy"}`
3. `GET /api/v1/health/ready` → DB, Redis, Celery status
4. `POST /api/v1/auth/login` → returns JWT tokens
5. `POST /api/v1/artworks/upload` (with Bearer token) → artwork created
6. `POST /api/v1/artworks/{id}/process` → Celery task dispatched
7. Flower dashboard at `http://localhost:5555` shows task
8. `GET /docs` → Swagger UI with auth
