# TaskFlow Backend

TaskFlow is a RESTful backend API for managing projects, tasks, user authentication, background notifications, and caching. Built with FastAPI, PostgreSQL, Redis, and Celery.

## Quick Start

### 1. Run with Docker Compose (Recommended)

Start the full stack (FastAPI app, PostgreSQL, Redis, Celery worker, and Celery beat) with a single command:

```bash
docker-compose up --build
```

Access the service once containers are running:
* **Interactive App Dashboard**: http://localhost:8000/
* **Swagger API Docs**: http://localhost:8000/docs
* **ReDoc API Docs**: http://localhost:8000/redoc

---

### 2. Local Manual Setup

If you prefer to run services locally outside Docker:

**Prerequisites**: Python 3.12, PostgreSQL 16, Redis 7.

1. **Install Python dependencies**:
   ```bash
   pip install .[dev]
   ```

2. **Set environment variables**:
   Create a `.env` file in the project root (or copy `.env.example`):
   ```bash
   cp .env.example .env
   ```

3. **Run database migrations**:
   ```bash
   python -m alembic upgrade head
   ```

4. **Start the API server**:
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Start background workers (optional for notifications)**:
   ```bash
   celery -A app.core.celery_app.celery_app worker --loglevel=info
   celery -A app.core.celery_app.celery_app beat --loglevel=info
   ```

---

## Core Features & Implementation Details

- **Authentication & Security**: Argon2id password hashing (`argon2-cffi`) and JWT access tokens (`PyJWT`).
- **Authorization**: Strict owner-level isolation for projects and tasks. Users cannot access, view, update, or delete projects or tasks belonging to another user.
- **Task Management**: Supports status tracking (`todo`, `in_progress`, `done`), assignees, due dates, filtering (`GET /tasks?status=...&assignee_id=...`), and pagination (`page`, `page_size`, `total`, `total_pages`).
- **Redis Caching**: `GET /tasks` responses are cached per user in Redis. Any task creation, update, deletion, or status change automatically invalidates the user's cached task listings.
- **Background Tasks**: Celery handles asynchronous task reassignment notifications and periodic overdue task checks (scheduled via Celery Beat) without generating duplicate unread notifications.
- **Observability**: Health checks at `GET /health` (verifies PostgreSQL and Redis) and Prometheus metrics at `GET /metrics`.

---

## Testing & Linting

Run automated tests:
```bash
pytest
```

Run linter:
```bash
ruff check .
```

Continuous Integration is configured via GitHub Actions in `.github/workflows/ci.yml`.

---

## Technical Design Decisions & Tradeoffs

* **FastAPI**: Provides native async capability, request validation via Pydantic v2, and auto-generated OpenAPI docs out of the box.
* **SQLAlchemy 2.0 & Alembic**: Explicit database queries and schema migration history rather than auto-creating tables at runtime.
* **Argon2id over bcrypt**: Uses modern memory-hard password hashing recommended by OWASP.
* **Redis Key Isolation**: Cache keys are scoped by user ID (`tasks:user:{user_id}:...`) to guarantee cross-tenant data isolation.
* **Celery & Redis**: Simple broker setup suitable for take-home scope while keeping background jobs decoupled from HTTP request loops.

---

## Project Structure

```text
├── alembic/              # Database migrations
├── app/
│   ├── api/              # API endpoints & auth dependencies
│   ├── core/             # App settings, security, Redis & Celery setup
│   ├── db/               # SQLAlchemy session & Base model
│   ├── models/           # User, Project, Task, Notification ORM models
│   ├── schemas/          # Pydantic request/response schemas
│   └── tasks/            # Celery background notification tasks
├── static/               # HTML/CSS/JS web dashboard interface
├── tests/                # Pytest unit & integration tests
├── docker-compose.yml    # Docker Compose multi-container setup
├── Dockerfile            # Container build specification
└── pyproject.toml        # Project dependencies & tool configurations
```
