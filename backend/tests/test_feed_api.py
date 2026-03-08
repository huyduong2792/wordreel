"""
Tests for Recommendation/Feed API endpoints.

Tests cover:
- Session initialization (logged-in and anonymous users)
- Watch event tracking
- Feed recommendations (cached and computed)
- Similar posts
- Pagination and filtering
"""
import pytest
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from database.supabase_client import get_supabase
from services.redis_client import get_redis_session_client
from services.container import get_recommendation_engine
from auth.utils import get_current_user_optional


# ==================== Mock Classes ====================

class MockUser:
    """Mock authenticated user"""
    def __init__(self, user_id: str = "user-123"):
        self.id = user_id


class MockRedisSessionClient:
    """Mock Redis client for session management"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.watches: Dict[str, List[Dict]] = {}
        self.recommendations: Dict[str, Dict] = {}
        self.ttl_extended: List[str] = []
    
    def create_session(
        self, 
        session_id: str, 
        user_id: Optional[str] = None,
        initial_watches: Optional[List[Dict]] = None
    ) -> bool:
        self.sessions[session_id] = {
            "user_id": user_id,
            "logged_in": user_id is not None
        }
        if initial_watches:
            self.watches[session_id] = initial_watches
        return True
    
    def get_session_user(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)
    
    def get_session_watches(self, session_id: str) -> List[Dict]:
        return self.watches.get(session_id, [])
    
    def track_watch(
        self,
        session_id: str,
        post_id: str,
        watch_percent: float,
        watch_duration: float,
        event_type: str = "progress"
    ) -> bool:
        if session_id not in self.watches:
            self.watches[session_id] = []
        
        # Find existing or create new
        for w in self.watches[session_id]:
            if w["post_id"] == post_id:
                w["watch_percent"] = max(w.get("watch_percent", 0), watch_percent)
                w["watch_duration"] = max(w.get("watch_duration", 0), watch_duration)
                return True
        
        self.watches[session_id].append({
            "post_id": post_id,
            "watch_percent": watch_percent,
            "watch_duration": watch_duration,
            "event_type": event_type
        })
        return True
    
    def get_cached_recommendations(self, session_id: str) -> Optional[Dict]:
        return self.recommendations.get(session_id)
    
    def cache_recommendations(
        self,
        session_id: str,
        post_ids: List[str],
        recommendation_type: str = "session"
    ) -> bool:
        self.recommendations[session_id] = {
            "post_ids": post_ids,
            "type": recommendation_type
        }
        return True
    
    def extend_session_ttl(self, session_id: str, user_id: Optional[str] = None) -> bool:
        self.ttl_extended.append(session_id)
        return True


class MockRecommendationEngine:
    """Mock recommendation engine"""
    
    def __init__(self):
        self.discovery_posts = ["post-1", "post-2", "post-3", "post-4", "post-5"]
        self.similar_posts = {}
        self.watch_history = {}
    
    async def get_discovery_feed(
        self,
        limit: int = 10,
        difficulty: str = "beginner",
        exclude_ids: Optional[List[str]] = None,
        allow_replay: bool = False
    ) -> List[str]:
        exclude_ids = exclude_ids or []
        result = [p for p in self.discovery_posts if p not in exclude_ids]
        
        # If all excluded and allow_replay, return all
        if not result and allow_replay:
            result = self.discovery_posts.copy()
        
        return result[:limit]
    
    async def get_watch_based_recommendations(
        self,
        session_watches: List[tuple],
        limit: int = 30,
        additional_exclude_ids: Optional[List[str]] = None
    ) -> List[str]:
        return ["rec-1", "rec-2", "rec-3", "rec-4", "rec-5"][:limit]
    
    async def get_similar_videos(
        self,
        video_id: str,
        limit: int = 5
    ) -> List[str]:
        return self.similar_posts.get(video_id, [])[:limit]
    
    async def load_user_watch_history(
        self,
        user_id: str,
        limit: int = 30
    ) -> List[tuple]:
        return self.watch_history.get(user_id, [])[:limit]
    
    async def get_all_watched_post_ids(self, user_id: str) -> List[str]:
        history = self.watch_history.get(user_id, [])
        return [post_id for post_id, _ in history]
    
    async def get_liked_post_ids(self, user_id: str) -> List[str]:
        return []


class MockSupabase:
    """Mock Supabase client"""
    
    def __init__(self):
        self.posts_data = []
        self.likes_data = []
        self.saves_data = []
        self._current_table = None
        self._filters = {}
        self._select_cols = "*"
    
    def table(self, name: str):
        self._current_table = name
        self._filters = {}
        return self
    
    def select(self, columns: str = "*"):
        self._select_cols = columns
        return self
    
    def eq(self, column: str, value: Any):
        self._filters[column] = ("eq", value)
        return self
    
    def in_(self, column: str, values: List[Any]):
        self._filters[column] = ("in", values)
        return self
    
    def execute(self):
        if self._current_table == "posts":
            return self._filter_posts()
        elif self._current_table == "post_likes":
            return MockResponse(self.likes_data)
        elif self._current_table == "saved_posts":
            return MockResponse(self.saves_data)
        return MockResponse([])
    
    def _filter_posts(self):
        result = self.posts_data.copy()
        
        for col, (op, value) in self._filters.items():
            if op == "eq":
                result = [r for r in result if r.get(col) == value]
            elif op == "in":
                result = [r for r in result if r.get(col) in value]
        
        return MockResponse(result)


class MockResponse:
    """Mock Supabase response"""
    def __init__(self, data: List[Dict]):
        self.data = data


# ==================== Fixtures ====================

@pytest.fixture
def mock_redis():
    return MockRedisSessionClient()


@pytest.fixture
def mock_recommendation_engine():
    return MockRecommendationEngine()


@pytest.fixture
def mock_supabase():
    return MockSupabase()


@pytest.fixture
def sample_posts():
    """Sample posts for testing"""
    posts = []
    for i in range(1, 6):
        posts.append({
            "id": f"post-{i}",
            "title": f"Test Video {i}",
            "description": f"Description for video {i}",
            "content_type": "video",
            "status": "ready",
            "video_url": f"http://cdn.example.com/video{i}.mp4",
            "hls_url": f"http://cdn.example.com/video{i}.m3u8",
            "thumbnail_url": f"http://cdn.example.com/thumb{i}.jpg",
            "duration": 60.0,
            "views_count": 100 * i,
            "likes_count": 10 * i,
            "comments_count": 5 * i,
            "tags": ["english", "beginner"],
            "difficulty_level": "beginner",
            "subtitles": [],
            "created_at": "2026-02-14T10:00:00Z",
            "updated_at": "2026-02-14T10:00:00Z"
        })
    return posts


@pytest.fixture
def client_with_mocks(mock_redis, mock_recommendation_engine, mock_supabase):
    """Test client with all feed-related dependencies mocked"""
    app.dependency_overrides[get_redis_session_client] = lambda: mock_redis
    app.dependency_overrides[get_recommendation_engine] = lambda: mock_recommendation_engine
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    app.dependency_overrides[get_current_user_optional] = lambda: None
    
    yield TestClient(app), mock_redis, mock_recommendation_engine, mock_supabase
    
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_user(mock_redis, mock_recommendation_engine, mock_supabase):
    """Test client with authenticated user"""
    app.dependency_overrides[get_redis_session_client] = lambda: mock_redis
    app.dependency_overrides[get_recommendation_engine] = lambda: mock_recommendation_engine
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    app.dependency_overrides[get_current_user_optional] = lambda: MockUser("user-123")
    
    yield TestClient(app), mock_redis, mock_recommendation_engine, mock_supabase
    
    app.dependency_overrides.clear()


# ==================== Session Init Tests ====================

class TestSessionInit:
    """Tests for POST /api/v1/recommendations/session/init"""
    
    def test_init_new_anonymous_session(self, client_with_mocks):
        """Should create a new session for anonymous user"""
        client, mock_redis, _, _ = client_with_mocks
        
        response = client.post(
            "/api/v1/recommendations/session/init",
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["is_new"] == True
        assert data["user_type"] == "anonymous"
        assert data["watches_count"] == 0
    
    def test_init_existing_valid_session(self, client_with_mocks):
        """Should return existing session if valid"""
        client, mock_redis, _, _ = client_with_mocks
        
        # Pre-create a session
        session_id = "existing-session-123"
        mock_redis.create_session(session_id, user_id=None)
        
        response = client.post(
            "/api/v1/recommendations/session/init",
            json={"existing_session_id": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["is_new"] == False
    
    def test_init_invalid_existing_session_creates_new(self, client_with_mocks):
        """Should create new session if existing session is invalid"""
        client, mock_redis, _, _ = client_with_mocks
        
        response = client.post(
            "/api/v1/recommendations/session/init",
            json={"existing_session_id": "invalid-session-id"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] != "invalid-session-id"
        assert data["is_new"] == True
    
    def test_init_session_for_logged_in_user(self, client_with_user):
        """Should create session with watch history for logged-in user"""
        client, mock_redis, mock_engine, _ = client_with_user
        
        # Add user's watch history
        mock_engine.watch_history["user-123"] = [
            ("post-1", 0.9),
            ("post-2", 0.5)
        ]
        
        response = client.post(
            "/api/v1/recommendations/session/init",
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_type"] == "logged_in"
        assert data["watches_count"] == 2


# ==================== Track Watch Tests ====================

class TestTrackWatch:
    """Tests for POST /api/v1/recommendations/track"""
    
    def test_track_watch_event_success(self, client_with_mocks):
        """Should track watch event successfully"""
        client, mock_redis, _, _ = client_with_mocks
        
        session_id = "session-123"
        mock_redis.create_session(session_id)
        
        response = client.post(
            "/api/v1/recommendations/track",
            json={
                "post_id": "post-123",
                "watch_percent": 0.85,
                "watch_duration": 45.5,
                "event_type": "pause"
            },
            headers={"X-Session-Id": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "tracked"
        
        # Verify watch was recorded
        watches = mock_redis.get_session_watches(session_id)
        assert len(watches) == 1
        assert watches[0]["post_id"] == "post-123"
        assert watches[0]["watch_percent"] == 0.85
    
    def test_track_watch_updates_with_higher_percent(self, client_with_mocks):
        """Should update existing watch if new percent is higher"""
        client, mock_redis, _, _ = client_with_mocks
        
        session_id = "session-123"
        mock_redis.create_session(session_id)
        
        # First watch at 50%
        client.post(
            "/api/v1/recommendations/track",
            json={"post_id": "post-123", "watch_percent": 0.5, "watch_duration": 30, "event_type": "progress"},
            headers={"X-Session-Id": session_id}
        )
        
        # Second watch at 90%
        client.post(
            "/api/v1/recommendations/track",
            json={"post_id": "post-123", "watch_percent": 0.9, "watch_duration": 54, "event_type": "finish"},
            headers={"X-Session-Id": session_id}
        )
        
        watches = mock_redis.get_session_watches(session_id)
        assert len(watches) == 1
        assert watches[0]["watch_percent"] == 0.9
    
    def test_track_watch_missing_session_header(self, client_with_mocks):
        """Should return 422 if session header is missing"""
        client, _, _, _ = client_with_mocks
        
        response = client.post(
            "/api/v1/recommendations/track",
            json={"post_id": "post-123", "watch_percent": 0.85, "watch_duration": 45.5, "event_type": "pause"}
        )
        
        assert response.status_code == 422


# ==================== Feed Tests ====================

class TestGetFeed:
    """Tests for GET /api/v1/recommendations/feed"""
    
    def test_get_feed_with_cached_recommendations(self, client_with_mocks, sample_posts):
        """Should return cached recommendations when available"""
        client, mock_redis, _, mock_supabase = client_with_mocks
        
        session_id = "session-123"
        mock_redis.create_session(session_id)
        mock_redis.cache_recommendations(session_id, ["post-1", "post-2", "post-3"], "session")
        mock_supabase.posts_data = sample_posts
        
        response = client.get(
            "/api/v1/recommendations/feed",
            params={"limit": 5},
            headers={"X-Session-Id": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation_type"] == "session"
        assert data["from_cache"] == True
        assert len(data["posts"]) == 3
    
    def test_get_feed_discovery_without_session(self, client_with_mocks, sample_posts):
        """Should return discovery feed when no session provided"""
        client, _, mock_engine, mock_supabase = client_with_mocks
        
        mock_engine.discovery_posts = ["post-1", "post-2", "post-3"]
        mock_supabase.posts_data = sample_posts
        
        response = client.get(
            "/api/v1/recommendations/feed",
            params={"limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation_type"] == "discovery"
        assert data["from_cache"] == False
    
    def test_get_feed_discovery_for_empty_session(self, client_with_mocks, sample_posts):
        """Should return discovery feed for session without cache"""
        client, mock_redis, mock_engine, mock_supabase = client_with_mocks
        
        session_id = "session-123"
        mock_redis.create_session(session_id)
        # No cache set
        
        mock_engine.discovery_posts = ["post-1", "post-2"]
        mock_supabase.posts_data = sample_posts
        
        response = client.get(
            "/api/v1/recommendations/feed",
            params={"limit": 5},
            headers={"X-Session-Id": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation_type"] == "discovery"
    
    def test_get_feed_excludes_watched_videos(self, client_with_mocks, sample_posts):
        """Should exclude videos user has already watched"""
        client, mock_redis, _, mock_supabase = client_with_mocks
        
        session_id = "session-123"
        mock_redis.create_session(session_id)
        mock_redis.track_watch(session_id, "post-1", 0.9, 60, "finish")
        mock_redis.cache_recommendations(session_id, ["post-1", "post-2", "post-3"], "session")
        mock_supabase.posts_data = sample_posts
        
        response = client.get(
            "/api/v1/recommendations/feed",
            params={"limit": 5},
            headers={"X-Session-Id": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        post_ids = [p["id"] for p in data["posts"]]
        assert "post-1" not in post_ids  # Watched video excluded
    
    def test_get_feed_pagination_with_offset(self, client_with_mocks, sample_posts):
        """Should support offset pagination"""
        client, mock_redis, _, mock_supabase = client_with_mocks
        
        session_id = "session-123"
        mock_redis.create_session(session_id)
        mock_redis.cache_recommendations(session_id, ["post-1", "post-2", "post-3", "post-4", "post-5"], "session")
        mock_supabase.posts_data = sample_posts
        
        # First page
        response1 = client.get(
            "/api/v1/recommendations/feed",
            params={"limit": 2, "offset": 0},
            headers={"X-Session-Id": session_id}
        )
        
        # Second page
        response2 = client.get(
            "/api/v1/recommendations/feed",
            params={"limit": 2, "offset": 2},
            headers={"X-Session-Id": session_id}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        page1_ids = {p["id"] for p in response1.json()["posts"]}
        page2_ids = {p["id"] for p in response2.json()["posts"]}
        
        # Pages should have different posts
        assert page1_ids.isdisjoint(page2_ids)
    
    def test_get_feed_extends_session_ttl(self, client_with_mocks, sample_posts):
        """Should extend session TTL on feed request"""
        client, mock_redis, _, mock_supabase = client_with_mocks
        
        session_id = "session-123"
        mock_redis.create_session(session_id)
        mock_redis.cache_recommendations(session_id, ["post-1"], "session")
        mock_supabase.posts_data = sample_posts
        
        client.get(
            "/api/v1/recommendations/feed",
            headers={"X-Session-Id": session_id}
        )
        
        assert session_id in mock_redis.ttl_extended
    
    def test_get_feed_allows_replay_when_all_watched(self, client_with_mocks, sample_posts):
        """Should allow replaying videos when user watched all"""
        client, mock_redis, mock_engine, mock_supabase = client_with_mocks
        
        session_id = "session-123"
        mock_redis.create_session(session_id)
        
        # User watched all available videos
        mock_redis.track_watch(session_id, "post-1", 1.0, 60, "finish")
        mock_redis.track_watch(session_id, "post-2", 1.0, 60, "finish")
        mock_redis.track_watch(session_id, "post-3", 1.0, 60, "finish")
        
        mock_engine.discovery_posts = ["post-1", "post-2", "post-3"]
        mock_supabase.posts_data = sample_posts
        
        response = client.get(
            "/api/v1/recommendations/feed",
            params={"limit": 5},
            headers={"X-Session-Id": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should still return posts (replay allowed)
        assert len(data["posts"]) > 0
    
    def test_get_feed_response_format(self, client_with_mocks, sample_posts):
        """Should return posts with all required fields"""
        client, mock_redis, _, mock_supabase = client_with_mocks
        
        session_id = "session-123"
        mock_redis.create_session(session_id)
        mock_redis.cache_recommendations(session_id, ["post-1"], "session")
        mock_supabase.posts_data = sample_posts
        
        response = client.get(
            "/api/v1/recommendations/feed",
            headers={"X-Session-Id": session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "posts" in data
        assert "recommendation_type" in data
        assert "from_cache" in data
        
        # Check post fields
        if data["posts"]:
            post = data["posts"][0]
            assert "id" in post
            assert "title" in post
            assert "content_type" in post
    
    def test_get_feed_with_invalid_session_falls_back_to_discovery(self, client_with_mocks, sample_posts):
        """Should fall back to discovery for invalid session"""
        client, mock_redis, mock_engine, mock_supabase = client_with_mocks
        
        mock_engine.discovery_posts = ["post-1", "post-2"]
        mock_supabase.posts_data = sample_posts
        
        response = client.get(
            "/api/v1/recommendations/feed",
            headers={"X-Session-Id": "invalid-session-id"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation_type"] == "discovery"


# ==================== Similar Posts Tests ====================

class TestSimilarPosts:
    """Tests for GET /api/v1/recommendations/similar/{post_id}"""
    
    def test_get_similar_posts_success(self, client_with_mocks, sample_posts):
        """Should return similar posts"""
        client, _, mock_engine, mock_supabase = client_with_mocks
        
        mock_engine.similar_posts["post-1"] = ["post-2", "post-3"]
        mock_supabase.posts_data = sample_posts
        
        response = client.get("/api/v1/recommendations/similar/post-1")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_similar_posts_empty_result(self, client_with_mocks, sample_posts):
        """Should return empty list if no similar posts found"""
        client, _, mock_engine, mock_supabase = client_with_mocks
        
        # Post exists but has no similar posts
        mock_engine.similar_posts = {"post-1": []}
        mock_supabase.posts_data = sample_posts
        
        response = client.get("/api/v1/recommendations/similar/post-1")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
