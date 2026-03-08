# AI Agent Development Flow

> ⚠️ **MANDATORY**: All AI agents MUST follow this development flow when making changes to the WordReel codebase.

---

## 1. Pre-Development Checklist

Before writing any code, AI agents MUST:

- [ ] **Understand the request**: Clarify ambiguous requirements with the user
- [ ] **Search existing code**: Use `grep_search` or `semantic_search` to find related code
- [ ] **Check for existing patterns**: Look at similar implementations in the codebase
- [ ] **Identify affected files**: List all files that need modification
- [ ] **Consider side effects**: Think about what else might break

---

## 2. Code Standards

### Backend (Python/FastAPI)

| Rule | Description |
|------|-------------|
| **Dependency Injection** | Use `Depends()` for all service dependencies in route handlers |
| **Type Hints** | All functions must have type hints for parameters and return values |
| **Pydantic Models** | Use Pydantic for request/response validation |
| **Async/Await** | Use async for I/O operations (DB, Redis, external APIs) |
| **Error Handling** | Use `HTTPException` with appropriate status codes |
| **Logging** | Use `structlog` for structured logging |

**Example - Correct Route Handler:**
```python
@router.get("/feed")
async def get_feed(
    limit: int = Query(5, ge=1, le=20),
    supabase: Client = Depends(get_supabase),           # ✅ Injected
    redis_client: RedisSessionClient = Depends(get_redis_session_client),  # ✅ Injected
) -> FeedResponse:                                       # ✅ Return type
    try:
        # Implementation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Frontend (React/TypeScript)

| Rule | Description |
|------|-------------|
| **Hooks at Top** | ALL React hooks MUST be called before any conditional returns |
| **TypeScript** | Use proper interfaces for props and state |
| **API Client** | Use `api.ts` for all backend calls |
| **Error Boundaries** | Handle errors gracefully with user feedback |
| **TailwindCSS** | Use Tailwind utilities, avoid inline styles |

**Example - Correct React Component:**
```typescript
const MyComponent = ({ isVisible, data }: Props) => {
    // ✅ ALL hooks at top, before any conditions
    const [state, setState] = useState(initial);
    const computed = useMemo(() => process(data), [data]);
    
    // ✅ Conditional returns AFTER hooks
    if (!isVisible) return null;
    
    return <div>...</div>;
};
```

---

## 3. Development Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI AGENT DEVELOPMENT FLOW                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Step 1: ANALYZE                                                             │
│  ├── Read related files to understand context                                │
│  ├── Search for existing patterns in codebase                                │
│  └── Identify all files that need changes                                    │
│                                                                              │
│  Step 2: PLAN                                                                │
│  ├── List all changes needed                                                 │
│  ├── Consider backward compatibility                                         │
│  └── Think about edge cases                                                  │
│                                                                              │
│  Step 3: IMPLEMENT                                                           │
│  ├── Make changes using edit tools (NOT printing codeblocks)                 │
│  ├── Follow code standards above                                             │
│  └── Update related files if needed                                          │
│                                                                              │
│  Step 4: TEST (REQUIRED for backend)                                         │
│  ├── Write tests for new functionality                                       │
│  ├── Run: python -m pytest tests/ -v                                         │
│  └── Ensure all tests pass before proceeding                                 │
│                                                                              │
│  Step 5: VERIFY                                                              │
│  ├── Check syntax: python -c "import ast; ast.parse(...)"                    │
│  ├── Check for import errors                                                 │
│  └── Test if containers need restart                                         │
│                                                                              │
│  Step 6: DEPLOY (if using Docker)                                            │
│  ├── Copy files to containers if code-only changes                           │
│  ├── Rebuild containers if dependencies changed                              │
│  └── Verify services are running                                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. File Change Rules

| Change Type | Action Required |
|-------------|-----------------|
| Python code only | `docker cp` to containers, may need restart |
| New Python package | Add to `requirements.txt`, rebuild containers |
| Docker config | `docker compose up -d` to apply |
| Frontend code | Auto hot-reload (Vite) |
| New npm package | `npm install` required |
| Database schema | Create migration in `database/migrations/` |
| Environment vars | Update `.env`, restart containers |

---

## 5. Verifying Changes

```bash
# Backend: Check syntax without cache issues
python3 -c "import ast; ast.parse(open('path/to/file.py').read())"

# Backend: Check container logs for errors
docker compose logs --tail=50 api
docker compose logs --tail=50 recommendation_worker

# Frontend: Check browser console for errors
# Frontend: Verify no TypeScript errors in IDE
```

---

## 6. Testing (REQUIRED for Backend)

> ⚠️ **MANDATORY**: All backend feature development MUST include tests before completion.

### Test Requirement Checklist

Before marking a backend feature as complete, AI agents MUST:

- [ ] **Write tests** for new functionality (API endpoints, services, business logic)
- [ ] **Run all tests** to ensure no regressions
- [ ] **Verify tests pass** - all tests must be green

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TESTING IS REQUIRED                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ❌ DO NOT skip testing for backend features                                 │
│  ❌ DO NOT mark feature complete without passing tests                       │
│  ❌ DO NOT ignore test failures                                              │
│                                                                              │
│  ✅ ALWAYS write tests for new API endpoints                                 │
│  ✅ ALWAYS run pytest before completing a feature                            │
│  ✅ ALWAYS fix failing tests before moving on                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Test Environment Setup (First Time Only)

```bash
cd backend

# Create pyenv virtualenv
pyenv virtualenv 3.10.0 wordreel
pyenv local wordreel

# Install all dependencies (includes test packages)
pip install -r requirements.txt
```

### Running Tests

```bash
cd backend

# Run all tests (REQUIRED before feature completion)
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_recommendation_engine.py -v

# Run specific test class
python -m pytest tests/test_feed_api.py::TestGetFeed -v

# Run single test
python -m pytest tests/test_redis_client.py::TestWatchTracking::test_watch_percent_keeps_higher_value -v

# Run with coverage report
python -m pytest tests/ --cov=. --cov-report=html
```

### Test Structure

```
backend/tests/
├── conftest.py                          # Shared fixtures & mocks
├── test_comments_api.py                 # Comment/like API tests
├── test_content_based_recommendations.py # Content recommendation algorithm tests
├── test_feed_api.py                     # Feed/recommendations API tests
├── test_recommendation_engine.py        # RecommendationEngine unit tests
├── test_recommendation_worker.py        # Worker background tasks
├── test_redis_client.py                 # Redis session management
```

### Writing Tests

**Use mock fixtures to isolate dependencies:**
```python
def test_my_feature(self, mock_redis_client, mock_recommendation_engine, mock_supabase):
    # Setup mocks
    mock_redis_client.create_session("session-123")
    mock_supabase.posts_data = [{"id": "post-1", ...}]
    
    # Execute
    result = my_function()
    
    # Assert
    assert result == expected
```

**For API tests, override FastAPI dependencies:**
```python
@pytest.fixture
def client_with_mocks(mock_redis, mock_supabase):
    """Test client with dependencies mocked"""
    app.dependency_overrides[get_redis_session_client] = lambda: mock_redis
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    
    yield TestClient(app)
    
    app.dependency_overrides.clear()

def test_api_endpoint(self, client_with_mocks):
    response = client_with_mocks.get(
        "/api/v1/recommendations/feed",
        headers={"X-Session-Id": "session-123"}
    )
    
    assert response.status_code == 200
```

### Test Categories

| Test Type | File Pattern | Purpose |
|-----------|--------------|---------|
| API Integration | `test_*_api.py` | Test HTTP endpoints with mocked deps |
| Unit Tests | `test_*.py` | Test service classes in isolation |
| Worker Tests | `test_*_worker.py` | Test background task logic |

### When Tests Are Required

| Scenario | Requirement |
|----------|-------------|
| New API endpoint | 🔴 **REQUIRED** - Integration tests |
| Bug fix | 🔴 **REQUIRED** - Regression test |
| Complex business logic | 🔴 **REQUIRED** - Unit tests |
| Security feature | 🔴 **REQUIRED** - Security tests |
| Simple refactoring | 🟡 Optional - But run existing tests |
| Frontend-only changes | 🟡 Optional - Manual test acceptable |

### Minimum Test Coverage

For new backend features, tests should cover:

1. **Happy path** - Normal successful operation
2. **Error cases** - Invalid input, missing data
3. **Edge cases** - Empty data, boundary values
4. **Authentication** - Both logged-in and anonymous users
5. **Validation** - Input sanitization, rate limiting

---

## 7. Common Mistakes to AVOID

| ❌ DON'T | ✅ DO |
|----------|------|
| Print codeblocks for file changes | Use `replace_string_in_file` or `create_file` tools |
| Add hooks after conditional returns | Put ALL hooks at component top |
| Fetch dependencies inside function body | Use `Depends()` in function signature |
| Hardcode configuration values | Use environment variables via `config.py` |
| Ignore error handling | Wrap in try/except with proper HTTP status |
| Make changes without reading context | Always search/read related files first |
| Forget to verify syntax | Always check syntax after edits |

---

## 8. Service Container Pattern

All services should be accessed through the dependency injection container:

```python
# ✅ Correct: Use DI container functions with Depends()
from services.container import get_recommendation_engine
from services.redis_client import get_redis_session_client
from database.supabase_client import get_supabase, get_service_supabase
from supabase import Client

@router.get("/endpoint")
async def handler(
    engine: RecommendationEngine = Depends(get_recommendation_engine),
    redis: RedisSessionClient = Depends(get_redis_session_client),
    supabase: Client = Depends(get_supabase),  # Regular client (RLS enforced)
):
    ...

@router.post("/endpoint")
async def handler(
    supabase: Client = Depends(get_service_supabase),  # Service client (bypasses RLS)
):
    ...

# ❌ Wrong: Direct instantiation or calling inside function
@router.get("/endpoint")
async def handler():
    engine = RecommendationEngine()  # Wrong!
    redis = get_redis_session_client()  # Wrong - should be Depends()
    supabase = get_supabase()  # Wrong - should be Depends()
```

### Supabase Client Types

| Client | Function | Use Case |
|--------|----------|----------|
| Regular | `get_supabase` | Read operations, RLS policies apply |
| Service | `get_service_supabase` | Write operations on behalf of user, bypasses RLS |

---

## 9. API Dependencies Pattern

Use the `api/dependencies.py` module for common route-level concerns:

### Rate Limiting

```python
from api.dependencies import RateLimiter, get_rate_limiter, get_comment_rate_limiter

# Option 1: Pre-configured rate limiter
@router.post("/comments")
async def create_comment(
    rate_limiter: RateLimiter = Depends(get_comment_rate_limiter),  # 10 req/min
    current_user = Depends(get_current_user)
):
    rate_limiter.check(current_user.id)  # Raises 429 if exceeded
    ...

# Option 2: Custom rate limiter
@router.post("/upload")
async def upload_file(
    rate_limiter: RateLimiter = Depends(get_rate_limiter("upload", 5, 300)),  # 5 per 5min
    current_user = Depends(get_current_user)
):
    rate_limiter.check(current_user.id)
    ...
```

### Input Sanitization

```python
from api.dependencies import InputSanitizer, get_sanitizer

@router.post("/comments")
async def create_comment(
    comment: CommentCreate,
    sanitizer: InputSanitizer = Depends(get_sanitizer)
):
    # Sanitizes and validates - raises 400 if empty after sanitization
    clean_content = sanitizer.sanitize_text(comment.content)
    ...
```

### Pre-configured Rate Limiters

| Dependency | Config | Use Case |
|-----------|--------|----------|
| `get_comment_rate_limiter` | 10 req/60s | Comments, likes |
| `get_like_rate_limiter` | 30 req/60s | Post likes/saves |
| `get_upload_rate_limiter` | 5 req/300s | File uploads |

### Adding New Dependencies

Add reusable dependencies to `api/dependencies.py`:

```python
# api/dependencies.py
def get_my_limiter() -> Callable[[], RateLimiter]:
    return get_rate_limiter("my_resource", max_requests=20, window_seconds=120)
```

---

## 10. Documentation Updates

When making significant changes:

1. Update instruction files if adding new patterns
2. Add docstrings to new functions/classes
3. Update API docs if changing endpoints
4. Add comments for complex logic

---

## Quick Reference Commands

```bash
# Start development
cd backend && docker compose up -d
cd web && npm run dev

# Check syntax
python3 -c "import ast; ast.parse(open('file.py').read())"

# Run tests (REQUIRED for backend features)
cd backend && python -m pytest tests/ -v
cd backend && python -m pytest tests/test_feed_api.py -v  # Specific file

# View logs
docker compose logs --tail=50 api
docker compose logs --tail=50 recommendation_worker

# Restart after code changes
docker compose restart api recommendation_worker
