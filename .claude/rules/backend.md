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

Queue names: `subtitle_processing`, `crawler`

## Logging
Use structlog for structured logging:
```python
import structlog

logger = structlog.get_logger()
logger.info("processing", post_id=post_id)
```

## Hot Reload
Backend auto-reloads with uvicorn `--reload`. For Docker: mount source volume.
