---
applyTo: "backend/**"
description: "Backend patterns, services, and code standards for FastAPI/Python"
---

# Backend Development Guide

## Code Standards

### Dependency Injection

Use `Depends()` for all service dependencies in route handlers:

```python
@router.get("/feed")
async def get_feed(
    limit: int = Query(5, ge=1, le=20),
    supabase: Client = Depends(get_supabase),           # ✅ Injected
    redis_client: RedisSessionClient = Depends(get_redis_session_client),
) -> FeedResponse:                                       # ✅ Return type
    try:
        # Implementation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Type Hints & Pydantic

- All functions must have type hints for parameters and return values
- Use Pydantic for request/response validation
- Use `async/await` for I/O operations (DB, Redis, external APIs)

**Pydantic Model with Aliases:**
```python
class Subtitle(BaseModel):
    subtitle_id: str = Field(alias="subtitleId")
    start_time: float = Field(alias="startTime")
    end_time: float = Field(alias="endTime")
    word_timings: List[WordTiming] = Field(alias="wordTimings")
    
    class Config:
        populate_by_name = True  # Accept both formats
```

### Security Patterns

**Always sanitize user input:**
```python
from api.dependencies import InputSanitizer, get_sanitizer

@router.post("/")
async def handler(
    data: UserInput,
    sanitizer: InputSanitizer = Depends(get_sanitizer)
):
    clean = sanitizer.sanitize_text(data.content)  # XSS protection
```

**Always rate limit write endpoints:**
```python
from api.dependencies import RateLimiter, get_rate_limiter

@router.post("/")
async def handler(
    rate_limiter: RateLimiter = Depends(get_rate_limiter("resource", 10, 60))
):
    rate_limiter.check(user_id)  # Raises 429 with X-RateLimit-* headers
```

---

## Core Services

### ContentProcessor (`services/content_processor.py`)

Main processing orchestrator with DI for AI services:

```python
class ContentProcessor:
    def __init__(
        self,
        video_processor: IVideoProcessor,
        quiz_generator: IQuizGenerator,
        embedding_service: IEmbeddingService
    ):
        ...
    
    def process_video(self, video_path: str, ...) -> ProcessingResult:
        """
        Pipeline:
        1. Get video info (duration)
        2. Extract audio (FFmpeg)
        3. Transcribe audio (AssemblyAI → word-level timestamps)
        4. Generate quiz (OpenAI GPT-4o-mini)
        5. Extract tags (OpenAI)
        6. Generate embedding (OpenAI text-embedding-3-small)
        """
```

### QuizGenerator (`services/quiz_generator.py`)

Generates quizzes with mixed question types:

| Type | Description | Frontend |
|------|-------------|----------|
| `multiple_choice` | 4 options, use `options[].is_correct` | Option buttons |
| `fill_blank` | Text input, use `correct_answer` | Text input |
| `true_false` | Boolean, use `correct_answer` ("true"/"false") | Two buttons |

### TUSClient (`services/tus_client.py`)

Resumable video uploads to CDN:

```python
client.upload_file_sync(file_path, metadata={
    "file_path": "/2025/01/15/video.mp4",
    "dash_qualities": "360,720",
    "hls_qualities": "720",
    "creator": "Attribution"
})
# Returns CDN URLs: video_url, hls_url, dash_url, thumbnail_url
```

---

## Celery Tasks

### Retry Pattern
```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def download_video_task(self, source_url: str):
    try:
        # Work here
    except Exception as e:
        raise self.retry(exc=e)  # Auto-retry with backoff
```

### Main Crawling Task Flow
```
download_video_task(source_url):
1. Check duplicate (source_url in posts)
2. Get source handler (TikTok, YouTube, etc.)
3. Download video (yt-dlp)
4. Process content (subtitles, quiz, embedding)
5. Upload to CDN (TUS)
6. Save to database
```

---

## Docker Operations

### Hot-Reload Code Changes

```bash
# Copy single file to container
docker cp backend/services/my_service.py backend-api-1:/app/services/

# Copy folder (note /. syntax)
docker cp backend/cli/. backend-api-1:/app/cli/
```

| Change Type | Action |
|-------------|--------|
| Python code only | `docker cp` + restart if needed |
| New Python package | `docker compose build` + `up -d` |
| docker-compose.yml | `docker compose up -d` |

### Useful Commands

```bash
# Check logs
docker compose logs -f celery_worker

# Restart after code changes
docker compose restart api celery_worker

# Rebuild containers
docker compose build --no-cache && docker compose up -d
```

---

## CLI Debug Tools

```bash
# Check session state
docker compose exec api python -m cli.check_session <session_id>

# Verbose mode
docker compose exec api python -m cli.check_session <session_id> -v

# List all sessions
docker compose exec api python -m cli.check_session --list
```

---

## File Structure

```
backend/
├── main.py                 # App entry, router registration
├── config.py               # Pydantic Settings from .env
├── celery_app.py           # Celery configuration
├── api/
│   ├── dependencies.py     # Rate limiting, sanitization
│   └── routes/             # API handlers
├── models/
│   └── schemas.py          # Pydantic models
├── services/
│   ├── container.py        # DI container
│   ├── content_processor.py
│   ├── video_processor.py
│   ├── quiz_generator.py
│   ├── embedding_service.py
│   ├── recommendation_engine.py
│   ├── redis_client.py
│   └── tus_client.py
├── workers/
│   └── recommendation_worker.py
└── tasks/
    └── crawler_tasks.py
```

---

## Environment Variables

Required in `backend/.env`:
```bash
SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET
OPENAI_API_KEY, ASSEMBLYAI_API_KEY
REDIS_HOST=redis (in Docker), localhost (native)
TUS_SERVER_URL, TUS_CREDENTIAL_ID, TUS_CREDENTIAL_SECRET, CDN_BASE_URL
```
