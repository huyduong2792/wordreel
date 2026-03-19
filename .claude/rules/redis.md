---
name: redis
scope: "backend/services/redis*.py,backend/workers/**"
priority: medium
---

# Redis Conventions

## Session Management
Sessions stored in Redis with TTLs:
```python
SESSION_TTL = 3600  # 1 hour for active sessions
WATCH_TTL = 86400   # 24 hours for watch tracking
```

## Watch Tracking
Track user watch progress for recommendations:
```python
# Key format: watch:{user_id}:{post_id}
# Value: JSON with progress, timestamp
redis.setex(f"watch:{user_id}:{post_id}", WATCH_TTL, json.dumps({
    "progress": 0.75,
    "timestamp": datetime.utcnow().isoformat(),
}))
```

## Recommendations Cache
Cache recommendation results:
```python
CACHE_TTL = 300  # 5 minutes
# Key: recommendations:{user_id}:{type}
```

## Celery Broker
Redis as Celery broker (configured via environment variables in docker-compose):
```python
broker_url = "redis://redis:6379/0"
result_backend = "redis://redis:6379/0"
```

## Watch Behavior
- Track: play/pause events, watch duration, completion percentage
- Prefetch next recommended content when user is 80% through current
- Use Redis pub/sub for real-time watch progress updates

## Prefetch System
When user starts watching a post:
1. Fetch recommendations for next 3 posts
2. Preload video manifests
3. Warm cache in Redis
