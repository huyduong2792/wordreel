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
