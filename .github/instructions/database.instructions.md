---
applyTo: "backend/database/**"
description: "Database schema, queries, and migration guide for Supabase PostgreSQL"
---

# Database Guide

## Schema Overview

### Main Tables

```sql
-- Content table
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type content_type NOT NULL DEFAULT 'video',
    title TEXT NOT NULL,
    description TEXT,
    video_url TEXT,
    hls_url TEXT,
    dash_url TEXT,
    thumbnail_url TEXT,
    duration DECIMAL(10,2),
    source_url TEXT UNIQUE,    -- Prevents duplicate crawls
    tags TEXT[],
    difficulty_level TEXT DEFAULT 'beginner',
    status post_status DEFAULT 'pending',
    embedding vector(1536),    -- For AI recommendations (pgvector)
    views_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Word-level subtitles (JSONB for flexibility)
CREATE TABLE subtitles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    language TEXT DEFAULT 'en',
    subtitles JSONB NOT NULL   -- Array of subtitle objects
);

-- AI-generated quizzes
CREATE TABLE quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    questions JSONB NOT NULL,   -- Array of QuizQuestion objects
    total_points INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- User quiz results
CREATE TABLE quiz_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    quiz_id UUID REFERENCES quizzes(id),
    post_id UUID REFERENCES posts(id),
    score INTEGER NOT NULL,
    total_points INTEGER NOT NULL,
    percentage DECIMAL(5,2),
    passed BOOLEAN,
    answers JSONB,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- User watch history
CREATE TABLE view_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    post_id UUID REFERENCES posts(id),
    watch_percent DECIMAL(5,2),
    watch_duration DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Enums
CREATE TYPE content_type AS ENUM ('video', 'image_slides', 'audio', 'quiz');
CREATE TYPE post_status AS ENUM ('pending', 'processing', 'transcribing', 'ready', 'failed');
```

---

## Subtitles JSONB Format

```json
{
  "subtitles": [
    {
      "subtitleId": "subtitle-1",
      "templateConfig": {"type": "color_highlight"},
      "text": "Hello everyone welcome to my channel",
      "startTime": 1.5,
      "endTime": 4.2,
      "wordTimings": [
        {"word": "Hello", "start": 1.5, "end": 1.9},
        {"word": "everyone", "start": 1.9, "end": 2.4},
        {"word": "welcome", "start": 2.4, "end": 2.8},
        {"word": "to", "start": 2.8, "end": 2.9},
        {"word": "my", "start": 2.9, "end": 3.2},
        {"word": "channel", "start": 3.2, "end": 4.2}
      ]
    }
  ]
}
```

**Important:** Backend transforms nested structure using `transform_post_data()` before returning to frontend.

---

## Critical: Data Transformation

When fetching posts with subtitles, ALWAYS use `transform_post_data()`:

```python
# Supabase returns nested structure, need to extract JSONB
post_data = transform_post_data(post_data)  # Flattens subtitles
posts.append(PostResponse(**post_data))
```

Without transformation: `subtitles.0.subtitleId Field required` error

---

## Common Queries

### Check latest posts
```sql
SELECT id, title, status, created_at 
FROM posts ORDER BY created_at DESC LIMIT 10;
```

### Check subtitles exist
```sql
SELECT post_id, jsonb_array_length(subtitles) as subtitle_count 
FROM subtitles WHERE post_id = 'uuid';
```

### Check quiz questions
```sql
SELECT id, jsonb_array_length(questions) as q_count 
FROM quizzes WHERE post_id = 'uuid';
```

### Find duplicate source URLs
```sql
SELECT source_url, COUNT(*) 
FROM posts GROUP BY source_url HAVING COUNT(*) > 1;
```

### Vector similarity search (recommendations)
```sql
SELECT id, title
FROM posts
WHERE id NOT IN (already_watched_ids)
  AND status = 'ready'
ORDER BY embedding <=> $user_embedding  -- cosine distance
LIMIT 30;
```

---

## Service Client Usage

**Use service client for bypassing RLS:**

```python
from database.supabase_client import get_service_supabase

# When inserting data on behalf of user
supabase = get_service_supabase()  # Bypasses Row Level Security
```

**Use regular client for user-scoped queries:**
```python
from database.supabase_client import get_supabase

supabase = get_supabase()  # Subject to RLS
```

---

## Migration Guide

### Creating Migrations

1. Create new SQL file in `backend/database/migrations/`:
   ```
   003_add_new_feature.sql
   ```

2. Include both UP and DOWN migrations:
   ```sql
   -- UP
   ALTER TABLE posts ADD COLUMN new_field TEXT;
   
   -- DOWN (comment for reference)
   -- ALTER TABLE posts DROP COLUMN new_field;
   ```

3. Apply via Supabase SQL editor or migration tool

### Existing Migrations

| File | Purpose |
|------|---------|
| `001_initial_schema.sql` | Base tables |
| `002_add_watch_percent.sql` | Watch tracking |
| `003_optimize_comments.sql` | Comment performance |
| `004_optimize_feed_recommendations.sql` | Feed indexes |

---

## pgvector Extension

Embeddings stored as `vector(1536)` type (OpenAI text-embedding-3-small):

```sql
-- Enable extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Cosine similarity distance
SELECT * FROM posts ORDER BY embedding <=> $query_embedding LIMIT 10;
```

**Lower distance = More similar**
