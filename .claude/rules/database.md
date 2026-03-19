---
name: database
scope: "backend/database/**"
priority: high
---

# Database Conventions

## Schema Overview
Key tables:
- `users` - User profiles (extends Supabase auth.users)
- `posts` - Unified content with `content_type` enum
- `subtitles` - Subtitle JSONB data
- `post_likes`, `saved_posts` - Engagement
- `comments` - Comment system
- `quizzes` - Quiz content
- `watch_history` - Learning progress

## transform_post_data()
ALL responses from Supabase MUST go through `transform_post_data()`:
```python
from backend.database.utils import transform_post_data

posts = supabase.from_("posts").select("*").execute()
transformed = [transform_post_data(p) for p in posts.data]
```

This function:
- Converts snake_case to camelCase for frontend
- Strips internal fields (e.g., raw embedding data)
- Normalizes date formats
- Handles null values

## Service vs Regular Client
```python
# Regular client - respects RLS policies (use for user-facing endpoints)
supabase = Depends(get_supabase)

# Admin client - bypasses RLS (use for admin endpoints only)
admin_supabase = Depends(get_admin_supabase)
```

## pgvector Similarity Search
Embeddings stored in `posts.embedding` (1536 dimensions, OpenAI text-embedding-3-small):
```python
# Find similar posts
result = supabase.rpc(
    "match_posts",
    {
        "query_embedding": embedding,
        "match_threshold": 0.7,
        "match_count": 10,
    }
).execute()
```

## Migrations
- Use Supabase migrations in `backend/database/migrations/`
- Never modify existing migrations
- New migrations for schema changes
