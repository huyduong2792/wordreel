---
name: crawl
description: Trigger content crawl from a source URL
disable-model-invocation: true
---

# Trigger Content Crawl

Trigger a content crawl from a source URL via the admin API.

**Usage:**
```
/crawl <source_url>
```

**Example:**
```
/crawl https://example.com/video-page
```

**Behind the scenes:**
```bash
curl -X POST http://localhost:8000/api/v1/admin/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "<source_url>", "user_id": "<user_id>"}'
```

**Notes:**
- Requires admin authentication
- Crawl runs asynchronously via Celery worker
- Check `/api/v1/admin/crawl/status/<task_id>` for status
- Valid source types: video pages, YouTube, TikTok URLs
