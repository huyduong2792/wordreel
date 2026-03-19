# CLAUDE.md

WordReel is a TikTok-style English learning platform with interactive subtitles, quizzes, and personalized recommendations. See `.claude/rules/` for detailed conventions.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.11+), Celery, Redis |
| Frontend | Astro 4.x, React 18, Tailwind CSS, hls.js |
| Database | Supabase (PostgreSQL + pgvector) |
| Auth | Supabase Auth (Email/Password, OAuth) |
| AI | OpenAI GPT-4, AssemblyAI |
| Upload | TUS Protocol |

## Directory Layout

```
wordreel/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── api/routes/          # API endpoints (posts, comments, quizzes, etc.)
│   ├── services/            # Business logic
│   ├── database/            # DB utilities (RLS, transform_post_data)
│   └── celery_app.py        # Celery configuration
├── web/                     # Astro + React frontend
├── CLAUDE.md                # This file
└── .claude/
    ├── rules/              # Detailed conventions (see below)
    ├── skills/              # Slash commands (/test-backend, /crawl, etc.)
    ├── agents/              # Custom agents (security-reviewer, test-runner)
    └── hooks/               # Pre/Post tool hooks
```

## Quick Commands

### Backend
```bash
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000  # API server
cd backend && python -m pytest -v                                  # Run tests
redis-server                                                      # Start Redis
celery -A celery_app worker -Q subtitle_processing,crawler         # Workers
```

### Frontend
```bash
cd web && npm run dev   # Dev server (http://localhost:4321)
cd web && npm run build # Production build
cd web && npm run check # Type check
```

### API
- Swagger UI: http://localhost:8000/docs
- All routes prefix: `/api/v1/`

## Detailed Conventions

Detailed conventions are in `.claude/rules/`. Key files:

| Rule | Scope | Content |
|------|-------|---------|
| `.claude/rules/overview.md` | global | Project overview, quick commands |
| `.claude/rules/backend.md` | `backend/**/*.py` | FastAPI DI, Pydantic, error handling, Celery |
| `.claude/rules/frontend.md` | `web/**/*` | React hooks order, TypeScript, TailwindCSS |
| `.claude/rules/testing.md` | `backend/tests/**` | pytest fixtures, mocking, coverage |
| `.claude/rules/database.md` | `backend/database/**` | Schema, transform_post_data, pgvector |
| `.claude/rules/security.md` | global | Credentials, XSS, rate limiting, RLS |
| `.claude/rules/redis.md` | `backend/services/redis*.py` | Sessions, watch tracking, recommendations |

## Key Patterns

- **Dependency injection**: `Depends(get_supabase)`, `Depends(get_current_user)`
- **Pydantic models**: All request/response bodies validated with type hints
- **Content types**: `video`, `image_slides`, `audio`, `quiz`
- **Post status**: `pending` → `processing` → `transcribing` → `ready` | `failed`
- **RLS**: Supabase Row Level Security handles all data access control
- **Embeddings**: pgvector (1536-dim, OpenAI text-embedding-3-small)
- **Video**: hls.js for HLS streaming with subtitle support
- **Slash commands**: `/test-backend`, `/test-frontend`, `/dev-start`, `/crawl`, `/db-query`, `/api-check`, `/review`
