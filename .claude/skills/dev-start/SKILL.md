---
name: dev-start
description: Start both backend and frontend dev servers
disable-model-invocation: true
---

# Start Development Servers

Start both backend and frontend development servers.

**Backend:**
```bash
cd backend && docker compose up -d
```

**Frontend:**
```bash
cd web && npm run dev
```

**Ports:**
- Frontend: http://localhost:4321
- Backend API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

**Hot Reload:**
- API server: auto-reloads (volume mount), no action needed.
- Celery workers: use `docker cp` + `docker restart` to save rebuild time.
  ```bash
  docker cp . backend-celery_worker-1:/app/ && docker restart backend-celery_worker-1
  docker cp . backend-recommendation_worker-1:/app/ && docker restart backend-recommendation_worker-1
  ```
- Only rebuild (`docker compose up -d --build`) when Dockerfile, dependencies, or system-level changes.
