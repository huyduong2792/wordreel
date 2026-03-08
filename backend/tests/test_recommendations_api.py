"""
Tests for Recommendation API endpoints.

Tests cover:
- Session initialization (logged-in and anonymous users)
- Watch event tracking
- Feed recommendations (cached and discovery fallback)
- Similar posts
- Trending posts
"""
import pytest
from fastapi.testclient import TestClient


class TestSessionInit:
    """Tests for POST /api/v1/recommendations/session/init"""
    
    def test_init_new_anonymous_session(self, client, mock_redis_client):
        """Should create a new session for anonymous user"""
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
    
    def test_init_existing_session(self, client, mock_redis_client, sample_session_id):
        """Should return existing session if valid"""
        # Pre-create a session
        mock_redis_client.create_session(sample_session_id, user_id=None)
        
        response = client.post(
            "/api/v1/recommendations/session/init",
            json={"existing_session_id": sample_session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == sample_session_id
        assert data["is_new"] == False
    
    def test_init_invalid_existing_session(self, client, mock_redis_client):
        """Should create new session if existing session is invalid"""
        response = client.post(
            "/api/v1/recommendations/session/init",
            json={"existing_session_id": "invalid-session-id"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] != "invalid-session-id"
        assert data["is_new"] == True


class TestTrackWatch:
    """Tests for POST /api/v1/recommendations/track"""
    
    def test_track_watch_event(self, client, mock_redis_client, sample_session_id):
        """Should track watch event successfully"""
        # Pre-create session
        mock_redis_client.create_session(sample_session_id)
        
        response = client.post(
            "/api/v1/recommendations/track",
            json={
                "post_id": "post-123",
                "watch_percent": 0.85,
                "watch_duration": 45.5,
                "event_type": "pause"
            },
            headers={"X-Session-Id": sample_session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "tracked"
        assert data["session_id"] == sample_session_id
        
        # Verify watch was recorded
        watches = mock_redis_client.get_session_watches(sample_session_id)
        assert len(watches) == 1
        assert watches[0]["post_id"] == "post-123"
        assert watches[0]["watch_percent"] == 0.85
    
    def test_track_watch_updates_existing(self, client, mock_redis_client, sample_session_id):
        """Should update existing watch with higher percent"""
        mock_redis_client.create_session(sample_session_id)
        
        # First watch
        client.post(
            "/api/v1/recommendations/track",
            json={
                "post_id": "post-123",
                "watch_percent": 0.5,
                "watch_duration": 30,
                "event_type": "progress"
            },
            headers={"X-Session-Id": sample_session_id}
        )
        
        # Second watch with higher percent
        client.post(
            "/api/v1/recommendations/track",
            json={
                "post_id": "post-123",
                "watch_percent": 0.9,
                "watch_duration": 54,
                "event_type": "finish"
            },
            headers={"X-Session-Id": sample_session_id}
        )
        
        watches = mock_redis_client.get_session_watches(sample_session_id)
        assert len(watches) == 1
        assert watches[0]["watch_percent"] == 0.9
    
    def test_track_watch_missing_session_header(self, client):
        """Should return 422 if session header is missing"""
        response = client.post(
            "/api/v1/recommendations/track",
            json={
                "post_id": "post-123",
                "watch_percent": 0.85,
                "watch_duration": 45.5,
                "event_type": "pause"
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestGetFeed:
    """Tests for GET /api/v1/recommendations/feed"""
    
    def test_get_feed_with_cached_recommendations(
        self, client, mock_redis_client, mock_supabase, sample_session_id, sample_posts
    ):
        """Should return cached recommendations if available"""
        # Setup: create session with cached recommendations
        mock_redis_client.create_session(sample_session_id)
        mock_redis_client.cache_recommendations(
            sample_session_id,
            ["post-1", "post-2", "post-3", "post-4", "post-5"],
            "session"
        )
        
        # Setup: add posts to mock database
        mock_supabase.posts_data = sample_posts
        
        response = client.get(
            "/api/v1/recommendations/feed",
            params={"limit": 5},
            headers={"X-Session-Id": sample_session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation_type"] == "session"
        assert data["from_cache"] == True
        assert len(data["posts"]) <= 5
    
    def test_get_feed_discovery_fallback(
        self, client, mock_redis_client, mock_recommendation_engine, mock_supabase, 
        sample_session_id, sample_posts
    ):
        """Should fall back to discovery feed if no cache"""
        # Setup: create session without cache
        mock_redis_client.create_session(sample_session_id)
        mock_recommendation_engine.discovery_posts = ["post-1", "post-2", "post-3"]
        mock_supabase.posts_data = sample_posts
        
        response = client.get(
            "/api/v1/recommendations/feed",
            params={"limit": 5},
            headers={"X-Session-Id": sample_session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation_type"] == "discovery"
    
    def test_get_feed_without_session(
        self, client, mock_recommendation_engine, mock_supabase, sample_posts
    ):
        """Should return discovery feed without session"""
        mock_recommendation_engine.discovery_posts = ["post-1", "post-2"]
        mock_supabase.posts_data = sample_posts
        
        response = client.get(
            "/api/v1/recommendations/feed",
            params={"limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["recommendation_type"] == "discovery"
    
    def test_get_feed_excludes_watched_videos(
        self, client, mock_redis_client, mock_supabase, sample_session_id, sample_posts
    ):
        """Should exclude watched videos from recommendations"""
        mock_redis_client.create_session(sample_session_id)
        
        # Track a watch
        mock_redis_client.track_watch(
            sample_session_id, "post-1", 0.9, 60, "finish"
        )
        
        # Cache recommendations including watched video
        mock_redis_client.cache_recommendations(
            sample_session_id,
            ["post-1", "post-2", "post-3", "post-4", "post-5"],
            "session"
        )
        
        mock_supabase.posts_data = sample_posts
        
        response = client.get(
            "/api/v1/recommendations/feed",
            params={"limit": 5},
            headers={"X-Session-Id": sample_session_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Watched video should be filtered out
        post_ids = [p["id"] for p in data["posts"]]
        assert "post-1" not in post_ids
    
    def test_get_feed_pagination(
        self, client, mock_redis_client, mock_supabase, sample_session_id, sample_posts
    ):
        """Should support offset pagination"""
        mock_redis_client.create_session(sample_session_id)
        mock_redis_client.cache_recommendations(
            sample_session_id,
            ["post-1", "post-2", "post-3", "post-4", "post-5"],
            "session"
        )
        mock_supabase.posts_data = sample_posts
        
        # Get first page
        response1 = client.get(
            "/api/v1/recommendations/feed",
            params={"limit": 2, "offset": 0},
            headers={"X-Session-Id": sample_session_id}
        )
        
        # Get second page
        response2 = client.get(
            "/api/v1/recommendations/feed",
            params={"limit": 2, "offset": 2},
            headers={"X-Session-Id": sample_session_id}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Pages should be different
        page1_ids = [p["id"] for p in response1.json()["posts"]]
        page2_ids = [p["id"] for p in response2.json()["posts"]]
        assert set(page1_ids).isdisjoint(set(page2_ids))


class TestSimilarPosts:
    """Tests for GET /api/v1/recommendations/similar/{post_id}"""
    
    def test_get_similar_posts(
        self, client, mock_recommendation_engine, mock_supabase, sample_posts
    ):
        """Should return similar posts"""
        mock_recommendation_engine.similar_posts["post-1"] = ["post-2", "post-3"]
        mock_supabase.posts_data = sample_posts
        
        response = client.get("/api/v1/recommendations/similar/post-1")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_similar_posts_not_found(self, client, mock_supabase):
        """Should return 404 if post doesn't exist"""
        mock_supabase.posts_data = []
        
        response = client.get("/api/v1/recommendations/similar/nonexistent")
        
        assert response.status_code == 404


class TestTrendingPosts:
    """Tests for trending posts endpoint - SKIPPED: endpoint not implemented"""
    
    @pytest.mark.skip(reason="/trending endpoint not implemented")
    def test_get_trending_posts(
        self, client, mock_recommendation_engine, mock_supabase, sample_posts
    ):
        """Should return trending posts"""
        mock_recommendation_engine.discovery_posts = ["post-1", "post-2", "post-3"]
        mock_supabase.posts_data = sample_posts
        
        response = client.get(
            "/api/v1/recommendations/trending",
            params={"limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
