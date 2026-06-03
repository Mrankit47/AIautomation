# AI Artwork Publishing Automation Platform

An enterprise-grade, production-ready backend platform designed to automate the ingestion, analysis, metadata generation, and multi-channel publishing of artwork images.

---

## 🚀 Key Features

*   **Production-Grade FastAPI Foundation**: Configured with asynchronous handlers, Pydantic Settings management, clean exception hierarchy, custom CORS middleware, and correlation ID tracking.
*   **Decoupled Workflow Orchestration**: Built-in support for **LangGraph** (version-controlled `v1`/`v2` workflows) and **CrewAI** agents/crews.
*   **Asynchronous Processing**: Scalable task processing using **Celery** with **Redis** as a broker and backend. Includes robust base tasks, retry policies, and structured logs.
*   **JWT Authentication**: Secure stateless authentication using `python-jose` for route protection and role management.
*   **Structured Logging**: Configured with `structlog` for high-performance JSON logs with automatic request context and correlation ID binding.
*   **Externalized Prompts**: Clean prompt management using version-controlled YAML files and Jinja2 templates, allowing hot-reloading from disk.
*   **Extensible Integrations Layer**: Abstract interfaces for Cloudinary storage and social media channels (Instagram, YouTube, Pinterest, TikTok).
*   **Robust Testing Suite**: Unit and integration test coverage with mocked Celery, Redis, and DB session fixtures.

---

## 📂 Project Structure

```
AIautomation/
├── backend/
│   ├── api/             # API Router & v1 endpoints (artwork, auth, health)
│   ├── auth/            # JWT Token creation, dependencies & service logic
│   ├── config/          # Environment configuration (pydantic-settings)
│   ├── core/            # Logging, middleware, exception classes & lifespan events
│   ├── database/        # Async SQLAlchemy session factory & repository base
│   ├── feature_flags/   # Runtime configuration toggles
│   ├── graph/           # LangGraph nodes, state, and workflow builder
│   ├── integrations/    # Social media & cloud storage client stubs
│   ├── models/          # Declarative SQLAlchemy ORM models (Artwork, User, WorkflowRun)
│   ├── prompts/         # Version-controlled Jinja2 prompt registry
│   ├── providers/       # Gemini AI api provider abstraction
│   ├── services/        # Business logic controllers
│   ├── tasks/           # Celery workers tasks & base classes
│   ├── workers/         # Celery worker process runner
│   └── workflows/       # Versioned execution pipelines (v1, v2)
├── docker/              # Dockerfiles (production, development)
├── alembic/             # Alembic migration configurations
├── scripts/             # Startup scripts (dev.sh, start.sh, start_celery.sh)
├── tests/               # Unit and integration test suites
└── docker-compose.yml   # Multi-container local orchestration
```

---

## 🛠️ Getting Started

### Prerequisites

*   Python 3.11+
*   PostgreSQL
*   Redis
*   Docker (Optional)

### Installation

1.  Clone the repository and navigate into it:
    ```bash
    cd AIautomation
    ```

2.  Set up a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements-dev.txt
    ```

4.  Configure environment variables:
    ```bash
    cp .env.example .env
    # Adjust database connection strings and JWT secrets in the .env file
    ```

---

## 💻 Running the Application

### Option A: Local Development

1.  Ensure PostgreSQL and Redis are running locally.
2.  Run migrations:
    ```bash
    alembic upgrade head
    ```
3.  Start the FastAPI server:
    ```bash
    ./scripts/dev.sh
    ```
4.  Start Celery workers:
    ```bash
    ./scripts/start_celery.sh
    ```

### Option B: Docker Compose (Development)

Build and run all services (FastAPI app, Celery worker, Flower dashboard, PostgreSQL, Redis) with hot-reloading:

```bash
docker-compose -f docker-compose.dev.yml up --build
```

Access services at:
*   **FastAPI API**: [http://localhost:8000](http://localhost:8000)
*   **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **Celery Flower Dashboard**: [http://localhost:5555](http://localhost:5555)

---

## 🧪 Running Tests

Run the test suite using `pytest`:

```bash
pytest tests/ -v
```
