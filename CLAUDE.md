# CLAUDE.md

This file provides guidance to Claude Opus (claude.ai/code) when working with code in this repository.

## Project Overview

WordReel is a TikTok-style English learning platform with interactive subtitles, quizzes, and personalized recommendations. The project consists of a **FastAPI backend** and an **Astro + React frontend**.

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: Supabase (PostgreSQL with pgvector for embeddings)
- **Auth**: Supabase Auth (Email/Password, OAuth)
- **Background Jobs**: Celery + Redis
- **Video Upload**: TUS Protocol (resumable uploads to cloud provider)
- **AI**: OpenAI GPT-4 (quiz generation), AssemblyAI (subtitles)

### Frontend
- **Framework**: Astro 4.x (server-side rendering)
- **UI**: React 18 + Tailwind CSS
- **Video**: hls.js for HLS streaming
- **Auth**: Supabase JS client

## Common Commands

### Backend (in `backend/` directory)
```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server
python main.py
# or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Start Redis (for background tasks)
redis-server

# Start Celery worker (for subtitle processing and crawler)
celery -A celery_app worker --loglevel=info -Q subtitle_processing,crawler

# Run tests
pytest

# Lint code
black .
flake8 .
```

### Frontend (in `web/` directory)
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Architecture

### API Structure (`backend/api/routes/`)
- `posts.py` - Unified content management (video, image_slides, audio, quiz)
- `comments.py` - Comment system
- `quizzes.py` - Quiz endpoints
- `recommendations.py` - Personalized and trending recommendations
- `tus.py` - Resumable upload handling
- `admin.py` - Admin endpoints

### Content Types
The platform supports 4 content types:
1. **video** - HLS/DASH streaming with subtitles
2. **image_slides** - Carousel of images with captions
3. **audio** - Audio content with transcript
4. **quiz** - Interactive quiz content

### Post Status Flow
`pending` → `processing` → `transcribing` → `ready` (or `failed`)

### Database Schema
Key tables in Supabase:
- `users` - User profiles (extends Supabase auth.users)
- `posts` - Unified content (video, slides, audio, quiz)
- `subtitles` - Subtitle/transcript data (JSONB)
- `post_likes`, `saved_posts` - User engagement
- `comments` - Comment system
- `quizzes` - Quiz questions and results
- `watch_history` - Learning progress tracking

### Recommendations System
- Uses pgvector for embeddings (OpenAI text-embedding-3-small, 1536 dimensions)
- Content-based filtering via vector similarity
- Collaborative filtering for trending/popular content

### Video Upload Flow
1. Client uploads video via TUS protocol to cloud provider
2. Backend registers video URL and processes metadata
3. Subtitles generated and stored in Supabase
4. Cloud provider handles HLS/DASH/thumbnail generation

## Key Configuration

### Environment Variables (backend/.env)
- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY` - Database
- `OPENAI_API_KEY` - Quiz generation (optional)
- `ASSEMBLYAI_API_KEY` - Subtitle generation
- `TUS_SERVER_URL`, `TUS_CREDENTIAL_ID`, `TUS_CREDENTIAL_SECRET` - Video upload
- `REDIS_HOST`, `REDIS_PORT` - Celery broker

### API Endpoints
- Swagger UI: http://localhost:8000/docs
- All API routes prefix: `/api/v1/`

## Development Notes

- Backend uses structured logging with `structlog` (JSON output)
- Service clients use dependency injection pattern (`get_supabase()`, `get_current_user`)
- Frontend uses Astro's server-side rendering with React islands for interactivity
- Supabase Row Level Security (RLS) policies handle data access control
