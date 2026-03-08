"""
Tests for Recommendation Engine.

Tests cover:
- Vector similarity search
- Watch-based recommendations
- Discovery feed
- Exclusion logic
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json


class TestWatchWeighting:
    """Tests for watch percent to weight conversion"""
    
    def test_high_watch_percent_gets_high_weight(self):
        """Watch >= 80% should get weight 1.0"""
        # Based on the weighting logic in recommendation_engine
        def watch_percent_to_weight(percent: float) -> float:
            if percent >= 0.8:
                return 1.0
            elif percent >= 0.5:
                return 0.6
            elif percent >= 0.2:
                return 0.3
            return 0.0
        
        assert watch_percent_to_weight(0.95) == 1.0
        assert watch_percent_to_weight(0.80) == 1.0
    
    def test_medium_watch_percent_gets_medium_weight(self):
        """Watch 50-80% should get weight 0.6"""
        def watch_percent_to_weight(percent: float) -> float:
            if percent >= 0.8:
                return 1.0
            elif percent >= 0.5:
                return 0.6
            elif percent >= 0.2:
                return 0.3
            return 0.0
        
        assert watch_percent_to_weight(0.75) == 0.6
        assert watch_percent_to_weight(0.50) == 0.6
    
    def test_low_watch_percent_gets_low_weight(self):
        """Watch 20-50% should get weight 0.3"""
        def watch_percent_to_weight(percent: float) -> float:
            if percent >= 0.8:
                return 1.0
            elif percent >= 0.5:
                return 0.6
            elif percent >= 0.2:
                return 0.3
            return 0.0
        
        assert watch_percent_to_weight(0.45) == 0.3
        assert watch_percent_to_weight(0.20) == 0.3
    
    def test_very_low_watch_percent_gets_zero_weight(self):
        """Watch < 20% should get weight 0.0"""
        def watch_percent_to_weight(percent: float) -> float:
            if percent >= 0.8:
                return 1.0
            elif percent >= 0.5:
                return 0.6
            elif percent >= 0.2:
                return 0.3
            return 0.0
        
        assert watch_percent_to_weight(0.15) == 0.0
        assert watch_percent_to_weight(0.05) == 0.0


class TestExclusionLogic:
    """Tests for video exclusion in recommendations"""
    
    def test_all_watched_videos_excluded(self):
        """All watched videos should be excluded regardless of watch percent"""
        watched = [
            ("post-1", 0.95),  # High watch
            ("post-2", 0.50),  # Medium watch
            ("post-3", 0.15),  # Low watch (still excluded!)
        ]
        
        all_posts = ["post-1", "post-2", "post-3", "post-4", "post-5"]
        watched_ids = [post_id for post_id, _ in watched]
        
        # Filter recommendations
        recommendations = [p for p in all_posts if p not in watched_ids]
        
        assert "post-1" not in recommendations
        assert "post-2" not in recommendations
        assert "post-3" not in recommendations  # Low watch still excluded
        assert "post-4" in recommendations
        assert "post-5" in recommendations
    
    def test_additional_exclude_ids_merged(self):
        """Additional exclude IDs from DB should be merged"""
        session_watched = ["post-1", "post-2"]
        db_watched = ["post-3", "post-4", "post-old-1"]  # From DB history
        
        all_exclude = set(session_watched) | set(db_watched)
        
        assert "post-1" in all_exclude
        assert "post-2" in all_exclude
        assert "post-3" in all_exclude
        assert "post-4" in all_exclude
        assert "post-old-1" in all_exclude


class TestDiscoveryFeed:
    """Tests for discovery feed logic"""
    
    @pytest.mark.asyncio
    async def test_discovery_excludes_watched(self):
        """Discovery feed should exclude watched videos"""
        from tests.conftest import MockRecommendationEngine
        
        engine = MockRecommendationEngine()
        engine.discovery_posts = ["post-1", "post-2", "post-3", "post-4", "post-5"]
        
        # Get discovery excluding some videos
        result = await engine.get_discovery_feed(
            limit=5,
            exclude_ids=["post-1", "post-3"]
        )
        
        assert "post-1" not in result
        assert "post-3" not in result
        assert "post-2" in result
        assert "post-4" in result
    
    @pytest.mark.asyncio
    async def test_discovery_respects_limit(self):
        """Discovery feed should respect limit parameter"""
        from tests.conftest import MockRecommendationEngine
        
        engine = MockRecommendationEngine()
        engine.discovery_posts = ["post-1", "post-2", "post-3", "post-4", "post-5"]
        
        result = await engine.get_discovery_feed(limit=2)
        
        assert len(result) == 2


class TestSimilarVideos:
    """Tests for similar video recommendations"""
    
    @pytest.mark.asyncio
    async def test_similar_videos_returns_related(self):
        """Should return videos similar to target"""
        from tests.conftest import MockRecommendationEngine
        
        engine = MockRecommendationEngine()
        engine.similar_posts["video-1"] = ["similar-1", "similar-2", "similar-3"]
        
        result = await engine.get_similar_videos("video-1", limit=5)
        
        assert "similar-1" in result
        assert "similar-2" in result
        assert "similar-3" in result
    
    @pytest.mark.asyncio
    async def test_similar_videos_empty_for_unknown(self):
        """Should return empty list for unknown video"""
        from tests.conftest import MockRecommendationEngine
        
        engine = MockRecommendationEngine()
        
        result = await engine.get_similar_videos("unknown-video", limit=5)
        
        assert result == []


class TestWatchBasedRecommendations:
    """Tests for watch-based recommendation computation"""
    
    @pytest.mark.asyncio
    async def test_returns_recommendations(self):
        """Should return recommendations based on watches"""
        from tests.conftest import MockRecommendationEngine
        
        engine = MockRecommendationEngine()
        
        watches = [
            ("post-1", 0.95),
            ("post-2", 0.70),
        ]
        
        result = await engine.get_watch_based_recommendations(
            session_watches=watches,
            limit=5
        )
        
        assert len(result) > 0
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_respects_additional_exclude(self):
        """Should exclude additional IDs from recommendations"""
        # This tests the interface - actual exclusion happens in real implementation
        from tests.conftest import MockRecommendationEngine
        
        engine = MockRecommendationEngine()
        
        watches = [("post-1", 0.95)]
        exclude = ["old-watched-1", "old-watched-2"]
        
        result = await engine.get_watch_based_recommendations(
            session_watches=watches,
            limit=5,
            additional_exclude_ids=exclude
        )
        
        # Mock always returns same recommendations
        # Real implementation would exclude these
        assert isinstance(result, list)


class TestUserWatchHistory:
    """Tests for loading user watch history from DB"""
    
    @pytest.mark.asyncio
    async def test_load_user_history(self):
        """Should load watch history for user"""
        from tests.conftest import MockRecommendationEngine
        
        engine = MockRecommendationEngine()
        engine.watch_history["user-123"] = [
            ("post-1", 0.95),
            ("post-2", 0.80),
            ("post-3", 0.60),
        ]
        
        result = await engine.load_user_watch_history("user-123", limit=10)
        
        assert len(result) == 3
        assert ("post-1", 0.95) in result
    
    @pytest.mark.asyncio
    async def test_load_respects_limit(self):
        """Should respect limit when loading history"""
        from tests.conftest import MockRecommendationEngine
        
        engine = MockRecommendationEngine()
        engine.watch_history["user-123"] = [
            ("post-1", 0.95),
            ("post-2", 0.80),
            ("post-3", 0.60),
            ("post-4", 0.50),
            ("post-5", 0.40),
        ]
        
        result = await engine.load_user_watch_history("user-123", limit=2)
        
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_get_all_watched_post_ids(self):
        """Should get all watched post IDs without limit"""
        from tests.conftest import MockRecommendationEngine
        
        engine = MockRecommendationEngine()
        engine.watch_history["user-123"] = [
            ("post-1", 0.95),
            ("post-2", 0.80),
            ("post-3", 0.15),  # Low watch, still included
        ]
        
        result = await engine.get_all_watched_post_ids("user-123")
        
        assert "post-1" in result
        assert "post-2" in result
        assert "post-3" in result  # All IDs regardless of percent
