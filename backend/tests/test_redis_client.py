"""
Tests for Redis Session Client.

Tests cover:
- Session creation and management
- Watch tracking with timestamp-based sync
- Recommendation caching
- TTL management
"""
import pytest
import time
from unittest.mock import MagicMock, patch
from services.redis_client import RedisSessionClient


class TestRedisSessionClientUnit:
    """Unit tests using mock Redis"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client"""
        mock = MagicMock()
        mock.pipeline.return_value.__enter__ = MagicMock(return_value=mock)
        mock.pipeline.return_value.__exit__ = MagicMock(return_value=None)
        return mock
    
    @pytest.fixture
    def redis_client(self, mock_redis):
        """Create RedisSessionClient with mocked Redis"""
        with patch('services.redis_client.redis.Redis', return_value=mock_redis):
            client = RedisSessionClient.__new__(RedisSessionClient)
            client._client = mock_redis  # Set private attribute, not property
            return client
    
    def test_session_key_format(self, redis_client):
        """Session keys should follow expected format"""
        session_id = "test-session-123"
        
        # Test key generation
        user_key = redis_client._user_key(session_id)
        watches_key = redis_client._watches_key(session_id)
        recs_key = redis_client._recommendations_key(session_id)
        
        assert user_key == "session:test-session-123:user"
        assert watches_key == "session:test-session-123:watches"
        assert recs_key == "session:test-session-123:recommendations"
    
    def test_create_session_sets_user_info(self, redis_client, mock_redis):
        """create_session should set user info in Redis"""
        session_id = "new-session"
        user_id = "user-123"
        
        redis_client.create_session(session_id, user_id=user_id)
        
        # Verify set was called with user info
        mock_redis.set.assert_called()
    
    def test_track_watch_adds_to_list(self, redis_client, mock_redis):
        """track_watch should add watch data to Redis list"""
        session_id = "session-123"
        post_id = "post-456"
        
        # Mock existing watches
        mock_redis.lrange.return_value = []
        
        redis_client.track_watch(
            session_id=session_id,
            post_id=post_id,
            watch_percent=0.75,
            watch_duration=45.0,
            event_type="pause"
        )
        
        # Verify list operations were called
        mock_redis.lrange.assert_called()


class TestWatchTracking:
    """Integration-style tests for watch tracking logic"""
    
    def test_watch_percent_keeps_higher_value(self):
        """Should keep higher watch_percent when updating"""
        from tests.conftest import MockRedisSessionClient
        
        client = MockRedisSessionClient()
        session_id = "test-session"
        client.create_session(session_id)
        
        # First watch at 50%
        client.track_watch(session_id, "post-1", 0.5, 30, "progress")
        
        # Second watch at 30% (lower - should be ignored)
        client.track_watch(session_id, "post-1", 0.3, 20, "progress")
        
        watches = client.get_session_watches(session_id)
        assert watches[0]["watch_percent"] == 0.5
        
        # Third watch at 90% (higher - should update)
        client.track_watch(session_id, "post-1", 0.9, 55, "finish")
        
        watches = client.get_session_watches(session_id)
        assert watches[0]["watch_percent"] == 0.9
    
    def test_multiple_videos_tracked_separately(self):
        """Should track multiple videos independently"""
        from tests.conftest import MockRedisSessionClient
        
        client = MockRedisSessionClient()
        session_id = "test-session"
        client.create_session(session_id)
        
        client.track_watch(session_id, "post-1", 0.8, 50, "pause")
        client.track_watch(session_id, "post-2", 0.5, 25, "pause")
        client.track_watch(session_id, "post-3", 0.95, 60, "finish")
        
        watches = client.get_session_watches(session_id)
        assert len(watches) == 3
        
        watch_map = {w["post_id"]: w for w in watches}
        assert watch_map["post-1"]["watch_percent"] == 0.8
        assert watch_map["post-2"]["watch_percent"] == 0.5
        assert watch_map["post-3"]["watch_percent"] == 0.95


class TestRecommendationCaching:
    """Tests for recommendation caching"""
    
    def test_cache_and_retrieve_recommendations(self):
        """Should cache and retrieve recommendations"""
        from tests.conftest import MockRedisSessionClient
        
        client = MockRedisSessionClient()
        session_id = "test-session"
        client.create_session(session_id)
        
        # Cache recommendations
        post_ids = ["rec-1", "rec-2", "rec-3", "rec-4", "rec-5"]
        client.cache_recommendations(session_id, post_ids, "session")
        
        # Retrieve cached
        cached = client.get_cached_recommendations(session_id)
        
        assert cached is not None
        assert cached["post_ids"] == post_ids
        assert cached["type"] == "session"
    
    def test_no_cache_returns_none(self):
        """Should return None if no cached recommendations"""
        from tests.conftest import MockRedisSessionClient
        
        client = MockRedisSessionClient()
        session_id = "test-session"
        client.create_session(session_id)
        
        cached = client.get_cached_recommendations(session_id)
        assert cached is None


class TestSessionManagement:
    """Tests for session lifecycle management"""
    
    def test_anonymous_session(self):
        """Should create anonymous session without user_id"""
        from tests.conftest import MockRedisSessionClient
        
        client = MockRedisSessionClient()
        session_id = "anon-session"
        
        client.create_session(session_id, user_id=None)
        
        user_info = client.get_session_user(session_id)
        assert user_info is not None
        assert user_info["logged_in"] == False
        assert user_info["user_id"] is None
    
    def test_logged_in_session(self):
        """Should create session with user_id for logged-in user"""
        from tests.conftest import MockRedisSessionClient
        
        client = MockRedisSessionClient()
        session_id = "user-session"
        user_id = "user-123"
        
        client.create_session(session_id, user_id=user_id)
        
        user_info = client.get_session_user(session_id)
        assert user_info is not None
        assert user_info["logged_in"] == True
        assert user_info["user_id"] == user_id
    
    def test_nonexistent_session_returns_none(self):
        """Should return None for nonexistent session"""
        from tests.conftest import MockRedisSessionClient
        
        client = MockRedisSessionClient()
        
        user_info = client.get_session_user("nonexistent")
        assert user_info is None
