---
name: testing
scope: "backend/tests/**"
priority: high
---

# Testing Conventions (pytest)

## Structure
```
backend/tests/
├── conftest.py          # Shared fixtures
├── test_posts.py
├── test_auth.py
└── ...
```

## conftest.py Fixtures
Use pytest fixtures for common setup:
```python
import pytest
from httpx import AsyncClient

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_headers():
    # Return auth headers with valid token
    ...

@pytest.fixture
def mock_supabase():
    # Mock Supabase client
    ...
```

## API Tests
Test endpoints with valid/invalid inputs:
```python
@pytest.mark.asyncio
async def test_create_post(client, auth_headers):
    response = await client.post(
        "/api/v1/posts",
        json={"title": "Test", "content_type": "video"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Test"
```

## Mocking
Use `pytest-mock` or `unittest.mock`:
```python
from unittest.mock import patch, AsyncMock

@patch("backend.services.supabase.get_supabase")
async def test_with_mock(mock_get, client):
    mock_get.return_value = MockSupabase()
    ...
```

## Coverage
- Minimum coverage: 70% for new code
- Run: `cd backend && python -m pytest --cov=. --cov-report=term-missing`

## When Tests Are Mandatory
- All new API endpoints
- Complex business logic in services
- Authentication/authorization flows
- Database queries (especially pgvector similarity search)
