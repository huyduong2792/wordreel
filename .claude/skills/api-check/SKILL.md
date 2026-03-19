---
name: api-check
description: Validate all API endpoints against Swagger docs
disable-model-invocation: true
---

# API Endpoint Check

Validate that all API endpoints are reachable and return expected responses.

**Full check via Swagger:**
```bash
curl -s http://localhost:8000/openapi.json | jq '.paths | keys'
```

**Check individual endpoints:**
```bash
# Health check
curl -s http://localhost:8000/api/v1/health

# Auth endpoints
curl -s http://localhost:8000/api/v1/auth/me

# Posts (requires auth)
curl -s -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/posts

# Recommendations
curl -s -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/recommendations/trending
```

**Swagger UI:** http://localhost:8000/docs

**Notes:**
- Ensure backend is running before checking
- Some endpoints require authentication - use a valid JWT token
- Check /api/v1/docs for OpenAPI specification
