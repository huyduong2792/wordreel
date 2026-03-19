---
name: backend
scope: "backend/**/*.py"
priority: high
---

# Backend Conventions (FastAPI)

## Dependency Injection
Use `Depends()` for all service dependencies:
```python
from fastapi import Depends

async def get_current_user(
    supabase: SupabaseClient = Depends(get_supabase),
) -> User:
    ...
```

## Pydantic Models
All request/response bodies must use Pydantic models with type hints:
```python
from pydantic import BaseModel, Field

class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content_type: ContentType
    metadata: dict | None = None
```

## Error Handling
Use HTTPException with consistent status codes:
- 400: Bad Request (validation error)
- 401: Unauthorized (missing/invalid auth)
- 403: Forbidden (insufficient permissions)
- 404: Not Found
- 429: Too Many Requests (rate limited)
- 500: Internal Server Error

```python
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="Post not found")
```

## Service Clients
Use the service client pattern for Supabase access:
```python
# Regular client (respects RLS)
supabase: SupabaseClient = Depends(get_supabase)

# Admin client (bypasses RLS)
admin_supabase: SupabaseClient = Depends(get_admin_supabase)
```

## Celery Tasks
Tasks go in `backend/workers/` or alongside routes:
```python
@celery_app.task
def process_subtitles(post_id: str):
    # Background processing
    ...
```

Queue names: `crawler` (see `backend/docker-compose.yml` for all services)

## Logging
Use structlog for structured logging:
```python
import structlog

logger = structlog.get_logger()
logger.info("processing", post_id=post_id)
```

## Hot Reload
**API server** — auto-reloads with uvicorn `--reload` (via volume mount), no action needed.

**Celery workers** — use `docker cp` to copy code + restart to save rebuild time:
```bash
# Restart celery worker (crawler queue)
docker cp . backend-celery_worker-1:/app/
docker restart backend-celery_worker-1

# Restart recommendation worker
docker cp . backend-recommendation_worker-1:/app/
docker restart backend-recommendation_worker-1
```

**Only rebuild** (`docker compose up -d --build`) when:
- Dockerfile changes
- New dependencies (requirements.txt)
- System-level changes

