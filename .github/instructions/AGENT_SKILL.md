# WordReel Agent Skill

> Quick reference for AI agents to understand and work with this project.

## Project Identity

**WordReel** is a TikTok-style English learning app with:
- Vertical video feed with snap scrolling
- Karaoke-style subtitles (word-by-word highlighting)
- AI-generated quizzes after each video
- Personalized recommendations based on watch history

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Astro 4.x + React 18 + TailwindCSS |
| Backend | FastAPI (Python 3.11+) |
| Database | Supabase PostgreSQL + pgvector |
| Cache/Session | Redis |
| Task Queue | Celery |
| AI | OpenAI GPT-4o-mini, AssemblyAI |
| Video | HLS/DASH streaming via CDN |
| Container | Docker Compose |

## Quick Commands

```bash
# Start backend
cd backend && docker compose up -d

# Start frontend (requires Node 22+)
cd web && npm run dev

# Check logs
docker compose -f backend/docker-compose.yml logs -f api

# Restart after code changes
docker compose -f backend/docker-compose.yml restart api
```

## Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /recommendations/session/init` | Create/restore session |
| `POST /recommendations/track` | Track watch events |
| `GET /recommendations/feed` | Get personalized feed |
| `GET /posts/feed` | Get general feed |
| `GET /quizzes/post/{id}` | Get quiz for video |
| `POST /admin/crawl` | Trigger video crawl |

## Critical Patterns

### 1. Subtitles Data Transformation
When fetching posts with subtitles, ALWAYS use `transform_post_data()`:
```python
# Supabase returns nested structure, need to extract JSONB
post_data = transform_post_data(post_data)  # Flattens subtitles
posts.append(PostResponse(**post_data))
```

### 2. React Hooks Order
All hooks MUST be called before any conditional returns:
```typescript
// ✅ CORRECT
const Component = () => {
    const [state, setState] = useState();
    const memo = useMemo(() => {}, []);
    if (!visible) return null;  // After hooks
    return <div/>;
};
```

### 3. Video Player Active State
Use cleanup function to prevent audio overlap:
```typescript
useEffect(() => {
    if (isActive) {
        const timeout = setTimeout(() => video.play(), 50);
        return () => {
            clearTimeout(timeout);
            video.pause();
            video.currentTime = 0;
        };
    }
}, [isActive]);
```

### 4. Session Header
Track API requires X-Session-Id header:
```typescript
headers: { 'X-Session-Id': sessionId }
```

## File Locations

| What | Where |
|------|-------|
| API routes | `backend/api/routes/` |
| Services | `backend/services/` |
| Pydantic schemas | `backend/models/schemas.py` |
| Redis client | `backend/services/redis_client.py` |
| Recommendation worker | `backend/workers/recommendation_worker.py` |
| Video player | `web/src/components/video/VideoPlayer.tsx` |
| Video feed | `web/src/components/video/VideoFeed.tsx` |
| API client | `web/src/lib/api.ts` |
| Full docs | `.github/instructions/.instructions.md` |

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `subtitles.0.subtitleId Field required` | Missing `transform_post_data()` | Add transformation before PostResponse |
| `Rendered fewer hooks` | Hooks after conditional | Move all hooks to top |
| Video not auto-playing | Missing cleanup | Add proper effect cleanup |
| Audio overlap | Previous video not paused | Use `video.pause()` in cleanup |
| 500 on /feed | No session header | Call `initSession()` first |

## Database Tables

- `posts` - Main content with video URLs, embeddings
- `subtitles` - JSONB with word-level timings
- `quizzes` - AI-generated questions
- `view_history` - User watch history with watch_percent
- `post_likes`, `saved_posts` - User interactions

## Environment Variables

Required in `backend/.env`:
```
SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY
OPENAI_API_KEY, ASSEMBLYAI_API_KEY
REDIS_HOST=redis (in Docker), localhost (native)
TUS_SERVER_URL, TUS_CREDENTIAL_ID, TUS_CREDENTIAL_SECRET
CDN_BASE_URL
```

## Docker Services

```
redis              - Session storage + Celery broker
api                - FastAPI server (port 8000)
celery_worker      - Video processing tasks
celery_beat        - Scheduled tasks
recommendation_worker - Redis→DB sync
```

## Version: 1.1.0 (February 2026)
