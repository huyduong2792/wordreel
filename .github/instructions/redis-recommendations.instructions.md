---
applyTo: "**/recommendations/**,**/redis**,**/workers/**"
description: "Redis session management and recommendation system architecture"
---

# Redis Recommendation System

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────────┐
│  Frontend       │────▶│  /session/init  │────▶│  Redis Session          │
│  VideoFeed      │     │                 │     │  session:{id}:watches   │
│                 │     │                 │     │  session:{id}:user      │
└────────┬────────┘     └─────────────────┘     │  session:{id}:recs      │
         │                                       └───────────┬─────────────┘
         │ Track events                                      │
         ▼                                                   │
┌─────────────────┐     ┌─────────────────┐                  ▼
│  VideoPlayer    │────▶│  /track         │     ┌─────────────────────────┐
│  trackWatch()   │     │                 │     │  Recommendation Worker  │
│                 │     │                 │     │  - Batch sync to DB     │
└─────────────────┘     └─────────────────┘     │  - Pre-compute recs     │
                                                 └─────────────────────────┘
```

---

## Redis Keys Structure

```
session:{session_id}:watches   → List of watch events (JSONB with timestamp)
session:{session_id}:user      → User info {user_id, logged_in}
session:{session_id}:recs      → Cached recommendations (5-min TTL)
pending_syncs                  → Set of session IDs needing DB sync
```

---

## Session Flow

### 1. Initialization

```
Frontend: api.initSession()
  ↓
POST /recommendations/session/init
  Body: { existing_session_id: "uuid-from-storage" }
  ↓
Backend:
  IF existing_session_id valid → extend TTL, return existing
  IF user just logged in → merge with DB history
  ELSE (new session) → create with UUID
    - IF logged in: Load last 30 watches from view_history
  ↓
Frontend: Store session_id in localStorage
```

### 2. Watch Tracking

Events tracked: `start`, `finish`, `pause`, `seek`, `progress` (every 5s)

```
POST /recommendations/track
Headers: { X-Session-Id: session_id }
Body: {
    post_id: "uuid",
    watch_percent: 0.85,      // 0.0 to 1.0
    watch_duration: 45.5,     // seconds
    event_type: "finish"
}
```

**Key behavior:**
- Keeps HIGHER watch_percent (doesn't decrease on replay)
- Last 50 watches only (sliding window)
- Logged-in users added to `pending_syncs` for DB write

### 3. Recommendation Feed

```
GET /recommendations/feed?limit=5
Headers: { X-Session-Id: session_id }
```

**No computation in API!** Returns:
- Cached recommendations if available
- Falls back to discovery feed (excludes watched)
- Worker pre-computes recommendations every 30s

---

## Background Worker

Two concurrent loops in `recommendation_worker.py`:

### Sync Loop (60s interval)
1. Get up to 50 sessions from `pending_syncs`
2. For each logged-in session:
   - Get watches before sync_start_time (race-safe)
   - UPSERT to view_history table
   - Re-add to pending if newer watches exist

### Recommendation Loop (30s interval)
1. SCAN for all `session:*:watches` keys
2. For each active session without cached recs:
   - Compute weighted average embedding
   - Vector similarity search
   - Cache recommendations (5-min TTL)

---

## Embedding Algorithm

### Watch Weight by Percentage

| Watch % | Weight | Description |
|---------|--------|-------------|
| ≥80% | 1.0 | Strong interest |
| 50-80% | 0.6 | Moderate interest |
| 20-50% | 0.3 | Light interest |
| <20% | 0.0 | Not used for embedding |

**Important:** ALL watched videos excluded from recommendations, regardless of watch %.

### User Profile Computation

```python
# watched_posts = [(post_A, 95%), (post_B, 60%), (post_C, 30%)]
# weights = [1.0, 0.6, 0.3]

user_embedding = (1.0 × embed_A + 0.6 × embed_B + 0.3 × embed_C)
                 ─────────────────────────────────────────────
                              (1.0 + 0.6 + 0.3)
```

### Similarity Search

```sql
SELECT id, title
FROM posts
WHERE id NOT IN (already_watched_ids)
  AND status = 'ready'
ORDER BY embedding <=> user_embedding  -- cosine distance
LIMIT 30;
```

---

## Session TTLs

| Type | Duration |
|------|----------|
| Logged-in users | 7 days |
| Anonymous users | 24 hours |
| Recommendation cache | 5 minutes |

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/recommendations/session/init` | POST | Create/restore session |
| `/recommendations/track` | POST | Track watch event |
| `/recommendations/feed` | GET | Get personalized feed |

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/services/redis_client.py` | Session management |
| `backend/workers/recommendation_worker.py` | Background sync |
| `backend/api/routes/recommendations.py` | API endpoints |
| `web/src/lib/api.ts` | Frontend session/tracking |

---

## Key Redis Client Methods

| Method | Purpose |
|--------|---------|
| `track_watch()` | Track event, update timestamp, mark for sync |
| `get_session_watches()` | Get all watches for session |
| `get_session_watches_before(ts)` | Get watches older than timestamp (safe sync) |
| `mark_session_synced(has_remaining)` | Remove from pending; re-add if needed |
| `cache_recommendations()` | Cache computed recs (5-min TTL) |

---

## Prefetch System

Frontend triggers prefetch when `activeIndex >= prefetchAt - 1`:

```typescript
// Feed returns 5 posts with prefetchAt: 4
// When user reaches post #4, fetch next batch
api.getRecommendedFeed(5)  // Appends to existing posts
```

**Duplicate filtering:** Frontend dedupes before appending
