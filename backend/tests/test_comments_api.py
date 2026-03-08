"""
Tests for Comment API endpoints.

Tests cover:
- Get comments for a post
- Create comment (with rate limiting and sanitization)
- Delete comment (with authorization)
- Like/unlike comment
"""
import pytest
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from database.supabase_client import get_supabase, get_service_supabase
from services.redis_client import get_redis_session_client
from api.dependencies import get_comment_rate_limiter, get_sanitizer, RateLimiter, InputSanitizer
from auth.utils import get_current_user, get_current_user_optional


# ==================== Mock Classes ====================

class MockUser:
    """Mock authenticated user"""
    def __init__(self, user_id: str = "user-123", email: str = "test@example.com"):
        self.id = user_id
        self.email = email
        self.user_metadata = {
            "name": "Test User",
            "avatar_url": "http://example.com/avatar.jpg"
        }


class MockSupabaseComments:
    """Mock Supabase client for comment tests"""
    
    def __init__(self):
        self.comments: List[Dict] = []
        self.users: List[Dict] = []
        self.comment_likes: List[Dict] = []
        self._current_table = None
        self._filters = {}
        self._select_cols = "*"
        self._order_col = None
        self._order_desc = False
        self._range_start = 0
        self._range_end = 50
        self._insert_data = None
        self._delete_mode = False
        self._upsert_data = None
    
    def table(self, name: str):
        self._current_table = name
        self._filters = {}
        self._delete_mode = False
        self._upsert_data = None
        self._insert_data = None
        self._update_data = None
        return self
    
    def select(self, columns: str = "*"):
        self._select_cols = columns
        return self
    
    def eq(self, column: str, value: Any):
        self._filters[column] = value
        return self
    
    def in_(self, column: str, values: List[Any]):
        self._filters[f"{column}_in"] = values
        return self
    
    def is_(self, column: str, value: Any):
        self._filters[f"{column}_is"] = value
        return self
    
    def order(self, column: str, desc: bool = False):
        self._order_col = column
        self._order_desc = desc
        return self
    
    def range(self, start: int, end: int):
        self._range_start = start
        self._range_end = end
        return self
    
    def insert(self, data: Dict):
        self._insert_data = data
        return self
    
    def upsert(self, data: Dict, on_conflict: str = None):
        self._upsert_data = data
        return self
    
    def delete(self):
        self._delete_mode = True
        return self
    
    def update(self, data: Dict):
        self._update_data = data
        return self
    
    def execute(self):
        if self._update_data:
            return self._handle_update()
        
        if self._upsert_data:
            # Upsert user
            user_id = self._upsert_data.get("id")
            existing = next((u for u in self.users if u["id"] == user_id), None)
            if existing:
                existing.update(self._upsert_data)
            else:
                self.users.append(self._upsert_data.copy())
            return MockResponse([self._upsert_data])
        
        if self._delete_mode:
            return self._handle_delete()
        
        if self._insert_data:
            return self._handle_insert()
        
        return self._handle_select()
    
    def _handle_select(self):
        if self._current_table == "post_comments":
            return self._select_comments()
        elif self._current_table == "users":
            return self._select_users()
        elif self._current_table == "comment_likes":
            return self._select_comment_likes()
        return MockResponse([])
    
    def _select_comments(self):
        result = self.comments.copy()
        
        if "post_id" in self._filters:
            result = [c for c in result if c["post_id"] == self._filters["post_id"]]
        
        if "id" in self._filters:
            result = [c for c in result if c["id"] == self._filters["id"]]
        
        if "parent_id_is" in self._filters:
            result = [c for c in result if c.get("parent_id") is None]
        
        if "parent_id" in self._filters:
            result = [c for c in result if c.get("parent_id") == self._filters["parent_id"]]
        
        # Add user data for joins
        if "users" in self._select_cols:
            for c in result:
                user = next((u for u in self.users if u["id"] == c["user_id"]), None)
                c["users"] = user or {"username": "Unknown", "avatar_url": None}
        
        return MockResponse(result)
    
    def _select_users(self):
        result = self.users.copy()
        if "id" in self._filters:
            result = [u for u in result if u["id"] == self._filters["id"]]
        # Return at least mock user data if user exists from upsert
        if not result and self._filters.get("id"):
            user_id = self._filters["id"]
            # Check if user was created via upsert
            user = next((u for u in self.users if u["id"] == user_id), None)
            if user:
                result = [user]
        return MockResponse(result)
    
    def _select_comment_likes(self):
        result = self.comment_likes.copy()
        if "comment_id" in self._filters:
            result = [l for l in result if l["comment_id"] == self._filters["comment_id"]]
        if "comment_id_in" in self._filters:
            result = [l for l in result if l["comment_id"] in self._filters["comment_id_in"]]
        if "user_id" in self._filters:
            result = [l for l in result if l["user_id"] == self._filters["user_id"]]
        return MockResponse(result)
    
    def _handle_insert(self):
        if self._current_table == "post_comments":
            new_comment = {
                "id": f"comment-{len(self.comments) + 1}",
                **self._insert_data,
                "created_at": datetime.now().isoformat() + "Z",
                "likes_count": 0,
                "replies_count": 0
            }
            self.comments.append(new_comment)
            return MockResponse([new_comment])
        
        elif self._current_table == "comment_likes":
            new_like = {
                "id": f"like-{len(self.comment_likes) + 1}",
                **self._insert_data
            }
            self.comment_likes.append(new_like)
            return MockResponse([new_like])
        
        return MockResponse([])
    
    def _handle_delete(self):
        if self._current_table == "post_comments":
            if "id" in self._filters:
                self.comments = [c for c in self.comments if c["id"] != self._filters["id"]]
        
        elif self._current_table == "comment_likes":
            if "id" in self._filters:
                self.comment_likes = [l for l in self.comment_likes if l["id"] != self._filters["id"]]
        
        return MockResponse([])
    
    def _handle_update(self):
        if self._current_table == "post_comments":
            if "id" in self._filters:
                for c in self.comments:
                    if c["id"] == self._filters["id"]:
                        c.update(self._update_data)
                        return MockResponse([c])
        return MockResponse([])


class MockResponse:
    """Mock Supabase response"""
    def __init__(self, data: List[Dict]):
        self.data = data


class MockRateLimiter:
    """Mock rate limiter that always allows"""
    def __init__(self, should_allow: bool = True):
        self.should_allow = should_allow
        self.check_count = 0
    
    def check(self, identifier: str):
        self.check_count += 1
        if not self.should_allow:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )


class MockRedisClient:
    """Mock Redis client for rate limiting tests"""
    def __init__(self):
        self.rate_limits = {}
    
    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int):
        current = self.rate_limits.get(key, 0) + 1
        self.rate_limits[key] = current
        return current <= max_requests, max(0, max_requests - current)


# ==================== Fixtures ====================

@pytest.fixture
def mock_supabase_comments():
    """Provide mock Supabase with comment data"""
    mock = MockSupabaseComments()
    # Add test user
    mock.users.append({
        "id": "user-123",
        "email": "test@example.com",
        "username": "Test User",
        "avatar_url": "http://example.com/avatar.jpg"
    })
    return mock


@pytest.fixture
def mock_user():
    """Provide mock authenticated user"""
    return MockUser()


@pytest.fixture
def mock_rate_limiter():
    """Provide mock rate limiter"""
    return MockRateLimiter()


@pytest.fixture
def client_with_mocks(mock_supabase_comments, mock_user, mock_rate_limiter):
    """Provide TestClient with all comment-related mocks"""
    app.dependency_overrides[get_supabase] = lambda: mock_supabase_comments
    app.dependency_overrides[get_service_supabase] = lambda: mock_supabase_comments
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_user_optional] = lambda: mock_user
    app.dependency_overrides[get_comment_rate_limiter] = lambda: mock_rate_limiter
    app.dependency_overrides[get_sanitizer] = lambda: InputSanitizer()
    
    yield TestClient(app), mock_supabase_comments, mock_user, mock_rate_limiter
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_comment():
    """Sample comment data"""
    return {
        "id": "comment-1",
        "post_id": "post-123",
        "user_id": "user-123",
        "content": "This is a test comment",
        "parent_id": None,
        "created_at": "2026-02-14T10:00:00Z",
        "likes_count": 5,
        "replies_count": 2
    }


# ==================== Tests ====================

class TestGetComments:
    """Tests for GET /api/v1/comments/post/{post_id}"""
    
    def test_get_comments_empty(self, client_with_mocks):
        """Should return empty list when no comments exist"""
        client, mock_db, _, _ = client_with_mocks
        
        response = client.get("/api/v1/comments/post/post-123")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_comments_with_data(self, client_with_mocks, sample_comment):
        """Should return comments for a post"""
        client, mock_db, _, _ = client_with_mocks
        mock_db.comments.append(sample_comment)
        
        response = client.get("/api/v1/comments/post/post-123")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["content"] == "This is a test comment"
        assert data[0]["user_name"] == "Test User"
    
    def test_get_comments_excludes_replies(self, client_with_mocks, sample_comment):
        """Should only return top-level comments (parent_id is null)"""
        client, mock_db, _, _ = client_with_mocks
        
        # Add top-level comment
        mock_db.comments.append(sample_comment)
        
        # Add reply
        reply = sample_comment.copy()
        reply["id"] = "comment-2"
        reply["parent_id"] = "comment-1"
        reply["content"] = "This is a reply"
        mock_db.comments.append(reply)
        
        response = client.get("/api/v1/comments/post/post-123")
        
        assert response.status_code == 200
        data = response.json()
        # Should only get top-level comment
        assert len(data) == 1
        assert data[0]["id"] == "comment-1"


class TestCreateComment:
    """Tests for POST /api/v1/comments/"""
    
    def test_create_comment_success(self, client_with_mocks):
        """Should create a new comment"""
        client, mock_db, mock_user, _ = client_with_mocks
        
        response = client.post(
            "/api/v1/comments/",
            json={
                "post_id": "post-123",
                "content": "Great video!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Great video!"
        assert data["user_id"] == mock_user.id
        assert data["post_id"] == "post-123"
        assert len(mock_db.comments) == 1
    
    def test_create_comment_sanitizes_content(self, client_with_mocks):
        """Should sanitize XSS attempts in content"""
        client, mock_db, _, _ = client_with_mocks
        
        response = client.post(
            "/api/v1/comments/",
            json={
                "post_id": "post-123",
                "content": "<script>alert('xss')</script>Hello"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # HTML should be escaped
        assert "<script>" not in data["content"]
        assert "&lt;script&gt;" in data["content"]
    
    def test_create_comment_empty_content_fails(self, client_with_mocks):
        """Should reject empty content"""
        client, _, _, _ = client_with_mocks
        
        response = client.post(
            "/api/v1/comments/",
            json={
                "post_id": "post-123",
                "content": "   "  # Whitespace only
            }
        )
        
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
    
    def test_create_comment_rate_limited(self, client_with_mocks):
        """Should enforce rate limiting"""
        client, mock_db, mock_user, mock_rate_limiter = client_with_mocks
        mock_rate_limiter.should_allow = False
        
        response = client.post(
            "/api/v1/comments/",
            json={
                "post_id": "post-123",
                "content": "Test comment"
            }
        )
        
        assert response.status_code == 429
        assert mock_rate_limiter.check_count == 1
    
    def test_create_comment_with_parent(self, client_with_mocks, sample_comment):
        """Should create a reply to existing comment"""
        client, mock_db, _, _ = client_with_mocks
        mock_db.comments.append(sample_comment)
        
        response = client.post(
            "/api/v1/comments/",
            json={
                "post_id": "post-123",
                "content": "This is a reply",
                "parent_id": "comment-1"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["parent_id"] == "comment-1"
    
    def test_create_reply_to_nonexistent_parent_fails(self, client_with_mocks):
        """Should reject reply to non-existent parent comment"""
        client, mock_db, _, _ = client_with_mocks
        
        response = client.post(
            "/api/v1/comments/",
            json={
                "post_id": "post-123",
                "content": "Reply to nothing",
                "parent_id": "nonexistent-comment"
            }
        )
        
        assert response.status_code == 404
        assert "parent comment not found" in response.json()["detail"].lower()
    
    def test_create_nested_reply_fails(self, client_with_mocks, sample_comment):
        """Should reject reply to a reply (only 1 level deep allowed)"""
        client, mock_db, _, _ = client_with_mocks
        
        # Add top-level comment
        mock_db.comments.append(sample_comment)
        
        # Add a reply to that comment
        reply = sample_comment.copy()
        reply["id"] = "comment-2"
        reply["parent_id"] = "comment-1"  # This is a reply
        reply["content"] = "First reply"
        mock_db.comments.append(reply)
        
        # Try to reply to the reply (should fail)
        response = client.post(
            "/api/v1/comments/",
            json={
                "post_id": "post-123",
                "content": "Reply to reply",
                "parent_id": "comment-2"  # Trying to reply to a reply
            }
        )
        
        assert response.status_code == 400
        assert "cannot reply to a reply" in response.json()["detail"].lower()


class TestDeleteComment:
    """Tests for DELETE /api/v1/comments/{comment_id}"""
    
    def test_delete_own_comment(self, client_with_mocks, sample_comment):
        """Should delete user's own comment"""
        client, mock_db, mock_user, _ = client_with_mocks
        mock_db.comments.append(sample_comment)
        
        response = client.delete("/api/v1/comments/comment-1")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Comment deleted"
        assert len(mock_db.comments) == 0
    
    def test_delete_other_user_comment_forbidden(self, client_with_mocks, sample_comment):
        """Should not allow deleting another user's comment"""
        client, mock_db, _, _ = client_with_mocks
        
        # Comment belongs to different user
        sample_comment["user_id"] = "other-user-456"
        mock_db.comments.append(sample_comment)
        
        response = client.delete("/api/v1/comments/comment-1")
        
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()
    
    def test_delete_nonexistent_comment(self, client_with_mocks):
        """Should return 404 for non-existent comment"""
        client, _, _, _ = client_with_mocks
        
        response = client.delete("/api/v1/comments/nonexistent-id")
        
        assert response.status_code == 404


class TestGetReplies:
    """Tests for GET /api/v1/comments/{comment_id}/replies"""
    
    def test_get_replies_empty(self, client_with_mocks, sample_comment):
        """Should return empty list when no replies exist"""
        client, mock_db, _, _ = client_with_mocks
        mock_db.comments.append(sample_comment)
        
        response = client.get("/api/v1/comments/comment-1/replies")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_replies_with_data(self, client_with_mocks, sample_comment):
        """Should return replies for a comment"""
        client, mock_db, _, _ = client_with_mocks
        
        # Add parent comment
        mock_db.comments.append(sample_comment)
        
        # Add replies
        reply1 = {
            "id": "reply-1",
            "post_id": "post-123",
            "user_id": "user-123",
            "parent_id": "comment-1",
            "content": "First reply",
            "created_at": "2026-02-14T11:00:00Z",
            "likes_count": 1,
            "replies_count": 0
        }
        reply2 = {
            "id": "reply-2",
            "post_id": "post-123",
            "user_id": "user-123",
            "parent_id": "comment-1",
            "content": "Second reply",
            "created_at": "2026-02-14T12:00:00Z",
            "likes_count": 0,
            "replies_count": 0
        }
        mock_db.comments.extend([reply1, reply2])
        
        response = client.get("/api/v1/comments/comment-1/replies")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["content"] == "First reply"
        assert data[1]["content"] == "Second reply"
    
    def test_get_replies_excludes_other_comments(self, client_with_mocks, sample_comment):
        """Should only return replies for the specified comment"""
        client, mock_db, _, _ = client_with_mocks
        
        # Add two parent comments
        mock_db.comments.append(sample_comment)
        other_comment = sample_comment.copy()
        other_comment["id"] = "comment-2"
        other_comment["content"] = "Other comment"
        mock_db.comments.append(other_comment)
        
        # Add reply to first comment only
        reply = {
            "id": "reply-1",
            "post_id": "post-123",
            "user_id": "user-123",
            "parent_id": "comment-1",
            "content": "Reply to first",
            "created_at": "2026-02-14T11:00:00Z",
            "likes_count": 0,
            "replies_count": 0
        }
        mock_db.comments.append(reply)
        
        # Get replies for comment-2 (should be empty)
        response = client.get("/api/v1/comments/comment-2/replies")
        
        assert response.status_code == 200
        assert response.json() == []


class TestLikeComment:
    """Tests for POST /api/v1/comments/{comment_id}/like"""
    
    def test_like_comment(self, client_with_mocks, sample_comment):
        """Should like a comment"""
        client, mock_db, _, _ = client_with_mocks
        mock_db.comments.append(sample_comment)
        
        response = client.post("/api/v1/comments/comment-1/like")
        
        assert response.status_code == 200
        assert response.json()["liked"] == True
        assert len(mock_db.comment_likes) == 1
    
    def test_unlike_comment(self, client_with_mocks, sample_comment):
        """Should unlike an already liked comment"""
        client, mock_db, mock_user, _ = client_with_mocks
        mock_db.comments.append(sample_comment)
        
        # Pre-existing like
        mock_db.comment_likes.append({
            "id": "like-1",
            "comment_id": "comment-1",
            "user_id": mock_user.id
        })
        
        response = client.post("/api/v1/comments/comment-1/like")
        
        assert response.status_code == 200
        assert response.json()["liked"] == False
        assert len(mock_db.comment_likes) == 0
    
    def test_like_comment_rate_limited(self, client_with_mocks, sample_comment):
        """Should enforce rate limiting on likes"""
        client, mock_db, _, mock_rate_limiter = client_with_mocks
        mock_db.comments.append(sample_comment)
        mock_rate_limiter.should_allow = False
        
        response = client.post("/api/v1/comments/comment-1/like")
        
        assert response.status_code == 429


class TestInputSanitization:
    """Tests for InputSanitizer"""
    
    def test_sanitize_removes_control_chars(self):
        """Should remove control characters"""
        sanitizer = InputSanitizer()
        content = "Hello\x00World\x1fTest"
        
        result = sanitizer.sanitize_text(content)
        
        assert "\x00" not in result
        assert "\x1f" not in result
        assert "Hello" in result
    
    def test_sanitize_normalizes_whitespace(self):
        """Should normalize excessive whitespace"""
        sanitizer = InputSanitizer()
        content = "Hello    World\n\n\nTest"
        
        result = sanitizer.sanitize_text(content)
        
        assert result == "Hello World Test"
    
    def test_sanitize_escapes_html(self):
        """Should escape HTML tags"""
        sanitizer = InputSanitizer()
        content = "<b>Bold</b> & <script>evil</script>"
        
        result = sanitizer.sanitize_text(content)
        
        assert "<b>" not in result
        assert "&lt;b&gt;" in result
        assert "&amp;" in result
    
    def test_sanitize_respects_max_length(self):
        """Should truncate to max_length"""
        sanitizer = InputSanitizer()
        content = "a" * 3000
        
        result = sanitizer.sanitize_text(content, max_length=100)
        
        assert len(result) == 100
    
    def test_sanitize_rejects_empty_after_processing(self):
        """Should reject content that becomes empty after sanitization"""
        sanitizer = InputSanitizer()
        content = "   \n\t   "  # Only whitespace
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            sanitizer.sanitize_text(content)
        
        assert exc_info.value.status_code == 400


class TestRateLimiter:
    """Tests for RateLimiter"""
    
    def test_rate_limiter_allows_under_limit(self):
        """Should allow requests under the limit"""
        mock_redis = MockRedisClient()
        limiter = RateLimiter(
            redis_client=mock_redis,
            resource="test",
            max_requests=5,
            window_seconds=60
        )
        
        # Should not raise for first request
        limiter.check("user-1")
        assert mock_redis.rate_limits["test:user-1"] == 1
    
    def test_rate_limiter_blocks_over_limit(self):
        """Should block requests over the limit"""
        mock_redis = MockRedisClient()
        # Pre-set to over limit
        mock_redis.rate_limits["test:user-1"] = 5
        
        limiter = RateLimiter(
            redis_client=mock_redis,
            resource="test",
            max_requests=5,
            window_seconds=60
        )
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            limiter.check("user-1")
        
        assert exc_info.value.status_code == 429
