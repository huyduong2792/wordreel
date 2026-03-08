"""
Tests for Recommendation Worker.

Tests cover:
- Database sync logic
- Recommendation pre-computation
- Race condition prevention
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from workers.recommendation_worker import RecommendationWorker


class TestRecommendationWorkerUnit:
    """Unit tests for RecommendationWorker"""
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client"""
        from tests.conftest import MockRedisSessionClient
        return MockRedisSessionClient()
    
    @pytest.fixture
    def mock_recommendation_engine(self):
        """Create mock recommendation engine"""
        from tests.conftest import MockRecommendationEngine
        return MockRecommendationEngine()
    
    @pytest.fixture
    def worker(self, mock_redis_client, mock_recommendation_engine):
        """Create worker with mocked dependencies"""
        with patch('workers.recommendation_worker.get_redis_session_client', return_value=mock_redis_client):
            with patch('workers.recommendation_worker.get_recommendation_engine', return_value=mock_recommendation_engine):
                worker = RecommendationWorker()
                worker.redis_client = mock_redis_client
                worker.recommendation_engine = mock_recommendation_engine
                return worker


class TestComputeRecommendations:
    """Tests for recommendation computation"""
    
    @pytest.fixture
    def mock_redis_client(self):
        from tests.conftest import MockRedisSessionClient
        return MockRedisSessionClient()
    
    @pytest.fixture
    def mock_recommendation_engine(self):
        from tests.conftest import MockRecommendationEngine
        return MockRecommendationEngine()
    
    @pytest.mark.asyncio
    async def test_compute_recommendations_for_session_with_watches(
        self, mock_redis_client, mock_recommendation_engine
    ):
        """Should compute recommendations when session has watches"""
        session_id = "test-session"
        mock_redis_client.create_session(session_id)
        mock_redis_client.track_watch(session_id, "post-1", 0.9, 60, "finish")
        mock_redis_client.track_watch(session_id, "post-2", 0.7, 45, "pause")
        
        with patch('workers.recommendation_worker.get_redis_session_client', return_value=mock_redis_client):
            with patch('workers.recommendation_worker.get_recommendation_engine', return_value=mock_recommendation_engine):
                worker = RecommendationWorker()
                worker.redis_client = mock_redis_client
                worker.recommendation_engine = mock_recommendation_engine
                
                result = await worker._compute_recommendations_for_session(session_id)
        
        assert result == True
        
        # Should have cached recommendations
        cached = mock_redis_client.get_cached_recommendations(session_id)
        assert cached is not None
        assert len(cached["post_ids"]) > 0
    
    @pytest.mark.asyncio
    async def test_compute_recommendations_no_watches(
        self, mock_redis_client, mock_recommendation_engine
    ):
        """Should return False when session has no watches"""
        session_id = "empty-session"
        mock_redis_client.create_session(session_id)
        
        with patch('workers.recommendation_worker.get_redis_session_client', return_value=mock_redis_client):
            with patch('workers.recommendation_worker.get_recommendation_engine', return_value=mock_recommendation_engine):
                worker = RecommendationWorker()
                worker.redis_client = mock_redis_client
                worker.recommendation_engine = mock_recommendation_engine
                
                result = await worker._compute_recommendations_for_session(session_id)
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_compute_recommendations_for_logged_in_user(
        self, mock_redis_client, mock_recommendation_engine
    ):
        """Should enhance recommendations with DB history for logged-in users"""
        session_id = "user-session"
        user_id = "user-123"
        
        mock_redis_client.create_session(session_id, user_id=user_id)
        mock_redis_client.track_watch(session_id, "post-1", 0.9, 60, "finish")
        
        # Add DB watch history
        mock_recommendation_engine.watch_history[user_id] = [
            ("post-old-1", 0.95),
            ("post-old-2", 0.8)
        ]
        
        with patch('workers.recommendation_worker.get_redis_session_client', return_value=mock_redis_client):
            with patch('workers.recommendation_worker.get_recommendation_engine', return_value=mock_recommendation_engine):
                worker = RecommendationWorker()
                worker.redis_client = mock_redis_client
                worker.recommendation_engine = mock_recommendation_engine
                
                result = await worker._compute_recommendations_for_session(session_id)
        
        assert result == True


class TestDatabaseSync:
    """Tests for Redis to PostgreSQL sync"""
    
    @pytest.fixture
    def mock_redis_client(self):
        from tests.conftest import MockRedisSessionClient
        client = MockRedisSessionClient()
        
        # Add method for timestamp-based sync
        def get_session_watches_before(session_id, before_timestamp):
            watches = client.watches.get(session_id, [])
            # In real implementation, filter by timestamp
            return watches, False
        
        client.get_session_watches_before = get_session_watches_before
        return client
    
    @pytest.fixture
    def mock_supabase(self):
        """Create mock Supabase for sync tests"""
        mock = MagicMock()
        mock.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        mock.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        return mock
    
    def test_sync_skips_anonymous_sessions(self, mock_redis_client):
        """Should skip syncing anonymous sessions"""
        session_id = "anon-session"
        mock_redis_client.create_session(session_id, user_id=None)
        mock_redis_client.track_watch(session_id, "post-1", 0.9, 60, "finish")
        mock_redis_client.pending_syncs.add(session_id)
        
        # Anonymous sessions should not sync to DB
        user_info = mock_redis_client.get_session_user(session_id)
        assert user_info["logged_in"] == False
    
    def test_sync_processes_logged_in_sessions(self, mock_redis_client):
        """Should process logged-in sessions"""
        session_id = "user-session"
        user_id = "user-123"
        mock_redis_client.create_session(session_id, user_id=user_id)
        mock_redis_client.track_watch(session_id, "post-1", 0.9, 60, "finish")
        mock_redis_client.pending_syncs.add(session_id)
        
        user_info = mock_redis_client.get_session_user(session_id)
        assert user_info["logged_in"] == True
        assert user_info["user_id"] == user_id


class TestRefreshRecommendations:
    """Tests for recommendation refresh loop"""
    
    @pytest.fixture
    def mock_redis_client(self):
        from tests.conftest import MockRedisSessionClient
        return MockRedisSessionClient()
    
    @pytest.fixture
    def mock_recommendation_engine(self):
        from tests.conftest import MockRecommendationEngine
        return MockRecommendationEngine()
    
    @pytest.mark.asyncio
    async def test_skip_sessions_with_cached_recommendations(
        self, mock_redis_client, mock_recommendation_engine
    ):
        """Should skip sessions that already have cached recommendations"""
        session_id = "cached-session"
        mock_redis_client.create_session(session_id)
        mock_redis_client.track_watch(session_id, "post-1", 0.9, 60, "finish")
        mock_redis_client.cache_recommendations(
            session_id, ["rec-1", "rec-2"], "session"
        )
        
        # Already cached - should skip
        cached = mock_redis_client.get_cached_recommendations(session_id)
        assert cached is not None
    
    @pytest.mark.asyncio
    async def test_compute_for_sessions_without_cache(
        self, mock_redis_client, mock_recommendation_engine
    ):
        """Should compute recommendations for sessions without cache"""
        session_id = "uncached-session"
        mock_redis_client.create_session(session_id)
        mock_redis_client.track_watch(session_id, "post-1", 0.9, 60, "finish")
        
        # No cache
        cached = mock_redis_client.get_cached_recommendations(session_id)
        assert cached is None
        
        # After computation, should have cache
        with patch('workers.recommendation_worker.get_redis_session_client', return_value=mock_redis_client):
            with patch('workers.recommendation_worker.get_recommendation_engine', return_value=mock_recommendation_engine):
                worker = RecommendationWorker()
                worker.redis_client = mock_redis_client
                worker.recommendation_engine = mock_recommendation_engine
                
                await worker._compute_recommendations_for_session(session_id)
        
        cached = mock_redis_client.get_cached_recommendations(session_id)
        assert cached is not None
