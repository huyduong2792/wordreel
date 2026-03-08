"""
Pytest configuration and fixtures for WordReel tests.

This file provides:
- Test client setup
- Mock services for dependency injection
- Sample test data factories
"""
import pytest
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

# Import the main app
from main import app

# Import services for mocking
from services.redis_client import RedisSessionClient, get_redis_session_client
from services.recommendation_engine import RecommendationEngine
from services.container import get_recommendation_engine
from database.supabase_client import get_supabase


# ==================== Mock Classes ====================

class MockRedisSessionClient:
    """Mock Redis client for testing"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self.watches: Dict[str, List[Dict]] = {}
        self.recommendations: Dict[str, Dict] = {}
        self.pending_syncs: set = set()
    
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
        return True
    
    def get_pending_sync_sessions(self, limit: int = 50) -> List[str]:
        return list(self.pending_syncs)[:limit]
    
    def mark_session_synced(self, session_id: str, has_remaining: bool = False) -> None:
        if session_id in self.pending_syncs:
            self.pending_syncs.discard(session_id)
        if has_remaining:
            self.pending_syncs.add(session_id)
    
    def get_all_sessions_for_recommendations(self, limit: int = 50) -> List[str]:
        return list(self.sessions.keys())[:limit]


class MockRecommendationEngine:
    """Mock recommendation engine for testing"""
    
    def __init__(self):
        self.discovery_posts = []
        self.similar_posts = {}
        self.watch_history = {}
    
    async def get_discovery_feed(
        self,
        limit: int = 10,
        difficulty: str = "beginner",
        exclude_ids: Optional[List[str]] = None,
        allow_replay: bool = True
    ) -> List[str]:
        exclude_ids = exclude_ids or []
        filtered = [p for p in self.discovery_posts if p not in exclude_ids][:limit]
        if not filtered and allow_replay:
            return self.discovery_posts[:limit]
        return filtered
    
    async def get_watch_based_recommendations(
        self,
        session_watches: List[tuple],
        limit: int = 30,
        additional_exclude_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> List[str]:
        # Return mock recommendations
        return ["rec-1", "rec-2", "rec-3", "rec-4", "rec-5"][:limit]
    
    async def get_similar_videos(
        self,
        video_id: str,
        limit: int = 5
    ) -> List[str]:
        return self.similar_posts.get(video_id, [])[:limit]
    
    async def get_trending_videos(self, limit: int = 10) -> List[str]:
        return self.discovery_posts[:limit]
    
    async def load_user_watch_history(
        self,
        user_id: str,
        limit: int = 30
    ) -> List[tuple]:
        return self.watch_history.get(user_id, [])[:limit]
    
    async def get_all_watched_post_ids(self, user_id: str) -> List[str]:
        history = self.watch_history.get(user_id, [])
        return [post_id for post_id, _ in history]


class MockSupabase:
    """Mock Supabase client for testing"""
    
    def __init__(self):
        self.posts_data = []
        self.subtitles_data = []
    
    def table(self, name: str):
        return MockSupabaseTable(self, name)


class MockSupabaseTable:
    """Mock Supabase table operations"""
    
    def __init__(self, client: MockSupabase, table_name: str):
        self.client = client
        self.table_name = table_name
        self._filters = {}
        self._select_cols = "*"
    
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
        # Return mock data based on table
        if self.table_name == "posts":
            data = self._filter_posts()
        else:
            data = []
        
        return MockResponse(data)
    
    def _filter_posts(self) -> List[Dict]:
        result = self.client.posts_data.copy()
        
        for col, (op, value) in self._filters.items():
            if op == "eq":
                result = [r for r in result if r.get(col) == value]
            elif op == "in":
                result = [r for r in result if r.get(col) in value]
        
        return result


class MockResponse:
    """Mock Supabase response"""
    
    def __init__(self, data: List[Dict]):
        self.data = data


# ==================== Fixtures ====================

@pytest.fixture
def mock_redis_client():
    """Provide a fresh mock Redis client"""
    return MockRedisSessionClient()


@pytest.fixture
def mock_recommendation_engine():
    """Provide a fresh mock recommendation engine"""
    return MockRecommendationEngine()


@pytest.fixture
def mock_supabase():
    """Provide a fresh mock Supabase client"""
    return MockSupabase()


@pytest.fixture
def client(mock_redis_client, mock_recommendation_engine, mock_supabase):
    """
    Provide a TestClient with all dependencies mocked.
    This is the main fixture for testing API endpoints.
    """
    # Override dependencies
    app.dependency_overrides[get_redis_session_client] = lambda: mock_redis_client
    app.dependency_overrides[get_recommendation_engine] = lambda: mock_recommendation_engine
    app.dependency_overrides[get_supabase] = lambda: mock_supabase
    
    yield TestClient(app)
    
    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def sample_post():
    """Sample post data for testing"""
    return {
        "id": "post-123",
        "title": "Test Video",
        "description": "A test video for learning",
        "content_type": "video",
        "status": "ready",
        "video_url": "http://cdn.example.com/video.mp4",
        "hls_url": "http://cdn.example.com/video.m3u8",
        "dash_url": "http://cdn.example.com/video.mpd",
        "thumbnail_url": "http://cdn.example.com/thumb.jpg",
        "duration": 60.0,
        "views_count": 100,
        "likes_count": 10,
        "comments_count": 5,
        "tags": ["english", "beginner"],
        "difficulty_level": "beginner",
        "subtitles": [],
        "created_at": "2026-02-14T10:00:00Z",
        "updated_at": "2026-02-14T10:00:00Z"
    }


@pytest.fixture
def sample_posts(sample_post):
    """List of sample posts"""
    posts = []
    for i in range(5):
        post = sample_post.copy()
        post["id"] = f"post-{i+1}"
        post["title"] = f"Test Video {i+1}"
        posts.append(post)
    return posts


@pytest.fixture
def sample_session_id():
    """Sample session ID"""
    return "session-test-123"


@pytest.fixture
def sample_user_id():
    """Sample user ID"""
    return "user-test-456"
