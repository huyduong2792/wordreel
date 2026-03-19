---
name: overview
scope: global
priority: lowest
---

# WordReel - Project Overview

## What is WordReel?
WordReel is a TikTok-style English learning platform with interactive subtitles, quizzes, and personalized recommendations. Supports video, image slides, audio, and quiz content.

## Tech Stack
- **Backend**: FastAPI (Python 3.11+) + Celery + Redis
- **Frontend**: Astro 4.x + React 18 + Tailwind CSS
- **Database**: Supabase (PostgreSQL + pgvector)
- **Auth**: Supabase Auth
- **AI**: OpenAI GPT-4 (quizzes), AssemblyAI (subtitles)
- **Upload**: TUS Protocol

## Directory Layout
```
wordreel/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── api/routes/          # API endpoints
│   ├── services/           # Business logic
│   ├── celery_app.py       # Celery configuration
│   └── database/           # DB utilities
├── web/                    # Astro + React frontend
├── CLAUDE.md              # This file
└── .claude/rules/         # Detailed conventions
```

## Quick Commands

### Backend (Docker Compose - recommended)
```bash
cd backend && docker compose up -d      # Start API, Redis, Celery workers, Celery beat, recommendation worker
cd backend && docker compose logs -f   # View logs
cd backend && docker compose down       # Stop all services
```

### Hot Reload (use instead of rebuilding)
**API server** — auto-reloads with `--reload`, no action needed.
**Celery workers** — copy updated code then restart:
```bash
docker cp . backend-celery_worker-1:/app/
docker restart backend-celery_worker-1

docker cp . backend-recommendation_worker-1:/app/
docker restart backend-recommendation_worker-1
```
Only rebuild (`docker compose up -d --build`) when: Dockerfile changes, new dependencies (requirements.txt), or system-level changes.


### Backend (local dev without Docker)
```bash
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000  # API server
cd backend && celery -A celery_app worker -Q crawler                # Celery worker
cd backend && celery -A celery_app beat --loglevel=info             # Celery beat
redis-server                                                       # Start Redis
cd backend && python -m pytest -v                                   # Run tests
```

### Frontend
```bash
cd web && npm run dev          # Dev server
cd web && npm run build        # Production build
cd web && npm run check        # Type check
```

## Key Conventions
- All API routes prefix: `/api/v1/`
- Service clients use dependency injection (`Depends()`)
- Content types: `video`, `image_slides`, `audio`, `quiz`
- Post status flow: `pending` → `processing` → `transcribing` → `ready` | `failed`
- Supabase RLS handles data access control
- See `.claude/rules/backend.md`, `.claude/rules/frontend.md`, etc. for detailed conventions
