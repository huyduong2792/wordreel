---
name: test-backend
description: Run pytest tests for the backend
disable-model-invocation: true
---

# Run Backend Tests

Run pytest with verbose output in the backend directory.

**Command:**
```bash
cd backend && python -m pytest -v
```

**Options:**
- `cd backend && python -m pytest` - run all tests
- `cd backend && python -m pytest tests/test_posts.py -v` - run specific test file
- `cd backend && python -m pytest --cov=. --cov-report=term-missing` - with coverage

**Notes:**
- Ensure Redis is running before testing Celery tasks
- Use `cd backend && python -m pytest -k "keyword"` to filter tests by keyword
