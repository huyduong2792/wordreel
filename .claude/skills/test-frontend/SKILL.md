---
name: test-frontend
description: Run TypeScript type check and lint for the frontend
disable-model-invocation: true
---

# Run Frontend Tests

Run TypeScript type checking and linting in the frontend directory.

**Commands:**
```bash
cd web && npm run check    # TypeScript type check
cd web && npm run lint     # ESLint
cd web && npm run test     # Unit tests (if configured)
```

**Notes:**
- `npm run check` validates all TypeScript types before build
- Fix any type errors before committing
