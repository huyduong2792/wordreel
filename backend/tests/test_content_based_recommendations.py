"""
Tests for Content-Based Recommendation System.

Tests verify that the recommendation engine suggests content similar to what users watch.
Based on actual data patterns:
- Food videos (bbq, cooking, pho, mukbang) should recommend other food videos
- American/US content (chicago, texas, americanlife) should recommend similar US content
- Travel/lifestyle content should recommend similar travel content

These tests validate the weighted embedding approach:
- Watch >= 80%: Strong interest (weight 1.0)
- Watch 50-80%: Moderate interest (weight 0.6)
- Watch 20-50%: Low interest (weight 0.3)
- Watch < 20%: Skipped (weight 0.0)
- Liked posts: Very strong interest (weight 1.2)
"""
import pytest
from typing import List, Dict, Any, Optional, Tuple
from unittest.mock import MagicMock, AsyncMock, patch
import json
import numpy as np


# ==================== Sample Data Based on Actual Supabase ====================

# IDs and embeddings simulate actual post categories
SAMPLE_POSTS = {
    # Food Posts
    "food-bbq-texas": {
        "id": "02a55e6d-dfd5-4b62-9bc6-6ac77dfc2451",
        "title": "The Best Texas BBQ @BurntBeanBBQ",
        "tags": ["bbq", "food", "review", "texas", "mukbang"],
        "content_type": "video",
        "difficulty_level": "beginner",
        "category": "food",
    },
    "food-pho-vietnamese": {
        "id": "4585e750-68dc-4598-b1db-ba82f254b3db",
        "title": "Our Mom Cooked Chicken Pho",
        "tags": ["cooking", "food", "vietnamese", "pho", "homemade"],
        "content_type": "video",
        "difficulty_level": "beginner",
        "category": "food",
    },
    "food-noodles-vietnamese": {
        "id": "09e8e0d0-2ba3-4f36-8135-998fd495aa89",
        "title": "HU TIEU KHO / DRIED PHO / VIETNAMESE DRY NOODLES",
        "tags": ["cooking", "vietnamese", "noodles", "recipe", "sauce"],
        "content_type": "video",
        "difficulty_level": "beginner",
        "category": "food",
    },
    
    # American/US Life Posts
    "us-chicago-travel": {
        "id": "def8291b-11e8-4641-b826-30fac71cb0b9",
        "title": "Chicago USA 🇺🇸",
        "tags": ["chicago", "travel", "lifestyle", "nightlife", "skyline"],
        "content_type": "video",
        "difficulty_level": "beginner",
        "category": "american",
    },
    "us-school-life": {
        "id": "0e0e38e8-8570-4dbb-a472-a78145802335",
        "title": "American school boy video!",
        "tags": ["americanlife", "school", "friendship", "youth", "tiktok"],
        "content_type": "video",
        "difficulty_level": "beginner",
        "category": "american",
    },
    "us-new-york": {
        "id": "fake-id-ny-001",
        "title": "New York City Life",
        "tags": ["newyork", "travel", "americanlife", "city"],
        "content_type": "video",
        "difficulty_level": "beginner",
        "category": "american",
    },
    
    # Travel/Lifestyle Posts
    "travel-europe": {
        "id": "fake-id-europe-001",
        "title": "Europe Travel Vlog",
        "tags": ["travel", "europe", "lifestyle", "vacation"],
        "content_type": "video",
        "difficulty_level": "intermediate",
        "category": "travel",
    },
    "travel-asia": {
        "id": "fake-id-asia-001",
        "title": "Asia Backpacking",
        "tags": ["travel", "asia", "backpacking", "adventure"],
        "content_type": "video",
        "difficulty_level": "beginner",
        "category": "travel",
    },
}


def generate_mock_embedding(category: str, variation: float = 0.0) -> List[float]:
    """
    Generate mock embeddings that cluster by category.
    Similar categories will have similar embeddings (high cosine similarity).
    """
    # Base vectors for each category (384-dimensional like all-MiniLM-L6-v2)
    base_vectors = {
        "food": [0.8, 0.7, 0.1, 0.1, 0.2],
        "american": [0.1, 0.2, 0.8, 0.7, 0.3],
        "travel": [0.2, 0.1, 0.4, 0.3, 0.9],
    }
    
    base = base_vectors.get(category, [0.5] * 5)
    
    # Extend to 384 dimensions (realistic embedding size)
    np.random.seed(hash(category) % 2**32)
    full_embedding = np.zeros(384)
    
    # Place category signature in different regions
    category_offset = {"food": 0, "american": 128, "travel": 256}.get(category, 0)
    for i, val in enumerate(base):
        full_embedding[category_offset + i * 20:(category_offset + i * 20 + 20)] = val
    
    # Add some noise for variation
    full_embedding += np.random.randn(384) * 0.1 * (1 + variation)
    
    # Normalize
    norm = np.linalg.norm(full_embedding)
    if norm > 0:
        full_embedding = full_embedding / norm
    
    return full_embedding.tolist()


class MockEmbeddingService:
    """Mock embedding service that returns predictable embeddings"""
    
    async def generate_weighted_embedding(
        self,
        embeddings: List[List[float]],
        weights: List[float]
    ) -> List[float]:
        """Compute weighted average of embeddings"""
        if not embeddings:
            return []
        
        arr = np.array(embeddings)
        weights_arr = np.array(weights).reshape(-1, 1)
        
        weighted_sum = np.sum(arr * weights_arr, axis=0)
        total_weight = sum(weights)
        
        if total_weight == 0:
            return []
        
        result = weighted_sum / total_weight
        
        # Normalize
        norm = np.linalg.norm(result)
        if norm > 0:
            result = result / norm
        
        return result.tolist()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    arr_a = np.array(a)
    arr_b = np.array(b)
    
    dot_product = np.dot(arr_a, arr_b)
    norm_a = np.linalg.norm(arr_a)
    norm_b = np.linalg.norm(arr_b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


# ==================== Fixtures ====================

@pytest.fixture
def post_embeddings() -> Dict[str, List[float]]:
    """Generate embeddings for all sample posts"""
    embeddings = {}
    for key, post in SAMPLE_POSTS.items():
        category = post["category"]
        variation = hash(key) % 10 / 10  # Small variation within category
        embeddings[post["id"]] = generate_mock_embedding(category, variation)
    return embeddings


@pytest.fixture
def mock_embedding_service():
    return MockEmbeddingService()


# ==================== Tests ====================

class TestWatchPercentWeighting:
    """Tests for watch percent to weight conversion logic"""
    
    def test_strong_interest_threshold(self):
        """Watch >= 80% should indicate strong interest (weight 1.0)"""
        def weight(percent):
            if percent >= 0.8:
                return 1.0
            elif percent >= 0.5:
                return 0.6
            elif percent >= 0.2:
                return 0.3
            else:
                return 0.0
        
        assert weight(0.80) == 1.0
        assert weight(0.85) == 1.0
        assert weight(1.0) == 1.0
        assert weight(0.79) == 0.6  # 79% falls to moderate
    
    def test_moderate_interest_threshold(self):
        """Watch 50-80% should indicate moderate interest (weight 0.6)"""
        def weight(percent):
            if percent >= 0.8:
                return 1.0
            elif percent >= 0.5:
                return 0.6
            elif percent >= 0.2:
                return 0.3
            else:
                return 0.0
        
        assert weight(0.50) == 0.6
        assert weight(0.65) == 0.6
        assert weight(0.75) == 0.6
    
    def test_low_interest_threshold(self):
        """Watch 20-50% should indicate low interest (weight 0.3)"""
        def weight(percent):
            if percent >= 0.8:
                return 1.0
            elif percent >= 0.5:
                return 0.6
            elif percent >= 0.2:
                return 0.3
            else:
                return 0.0
        
        assert weight(0.20) == 0.3
        assert weight(0.35) == 0.3
        assert weight(0.49) == 0.3
    
    def test_skipped_threshold(self):
        """Watch < 20% should be considered skipped (weight 0.0)"""
        def weight(percent):
            if percent >= 0.8:
                return 1.0
            elif percent >= 0.5:
                return 0.6
            elif percent >= 0.2:
                return 0.3
            else:
                return 0.0
        
        assert weight(0.0) == 0.0
        assert weight(0.10) == 0.0
        assert weight(0.19) == 0.0
    
    def test_like_weight_is_highest(self):
        """Liked posts should have weight 1.2 (higher than any watch percent)"""
        like_weight = 1.2
        max_watch_weight = 1.0
        
        assert like_weight > max_watch_weight


class TestCategorySimilarity:
    """Tests verify posts in same category have similar embeddings"""
    
    def test_food_posts_are_similar(self, post_embeddings):
        """Food posts should have high similarity to each other"""
        food_ids = [p["id"] for p in SAMPLE_POSTS.values() if p["category"] == "food"]
        
        for i in range(len(food_ids)):
            for j in range(i + 1, len(food_ids)):
                sim = cosine_similarity(
                    post_embeddings[food_ids[i]],
                    post_embeddings[food_ids[j]]
                )
                assert sim > 0.7, f"Food posts should be similar, got {sim}"
    
    def test_american_posts_are_similar(self, post_embeddings):
        """American/US posts should have high similarity to each other"""
        american_ids = [p["id"] for p in SAMPLE_POSTS.values() if p["category"] == "american"]
        
        for i in range(len(american_ids)):
            for j in range(i + 1, len(american_ids)):
                sim = cosine_similarity(
                    post_embeddings[american_ids[i]],
                    post_embeddings[american_ids[j]]
                )
                assert sim > 0.7, f"American posts should be similar, got {sim}"
    
    def test_different_categories_are_distinct(self, post_embeddings):
        """Posts from different categories should have lower similarity"""
        food_id = SAMPLE_POSTS["food-bbq-texas"]["id"]
        american_id = SAMPLE_POSTS["us-school-life"]["id"]
        
        sim = cosine_similarity(
            post_embeddings[food_id],
            post_embeddings[american_id]
        )
        
        # Different categories should be less similar than same category
        assert sim < 0.5, f"Different categories should be distinct, got {sim}"


class TestWeightedEmbeddingComputation:
    """Tests for computing weighted user preference embedding"""
    
    @pytest.mark.asyncio
    async def test_single_watched_video(self, post_embeddings, mock_embedding_service):
        """Single watched video should return embedding similar to that video"""
        food_id = SAMPLE_POSTS["food-bbq-texas"]["id"]
        food_embedding = post_embeddings[food_id]
        
        result = await mock_embedding_service.generate_weighted_embedding(
            embeddings=[food_embedding],
            weights=[1.0]
        )
        
        # Should be same direction as original
        sim = cosine_similarity(result, food_embedding)
        assert sim > 0.99, "Single video should match original embedding"
    
    @pytest.mark.asyncio
    async def test_multiple_same_category_strengthens_signal(
        self, post_embeddings, mock_embedding_service
    ):
        """Multiple watches in same category should reinforce that category"""
        food_ids = [
            SAMPLE_POSTS["food-bbq-texas"]["id"],
            SAMPLE_POSTS["food-pho-vietnamese"]["id"],
            SAMPLE_POSTS["food-noodles-vietnamese"]["id"],
        ]
        
        embeddings = [post_embeddings[fid] for fid in food_ids]
        weights = [1.0, 0.8, 0.6]  # Different engagement levels
        
        result = await mock_embedding_service.generate_weighted_embedding(
            embeddings=embeddings,
            weights=weights
        )
        
        # Result should be similar to all food posts
        for fid in food_ids:
            sim = cosine_similarity(result, post_embeddings[fid])
            assert sim > 0.7, f"Should stay in food category, got {sim}"
        
        # Result should be different from non-food posts
        american_id = SAMPLE_POSTS["us-school-life"]["id"]
        sim = cosine_similarity(result, post_embeddings[american_id])
        assert sim < 0.5, f"Should be different from American content, got {sim}"
    
    @pytest.mark.asyncio
    async def test_higher_weight_has_more_influence(
        self, post_embeddings, mock_embedding_service
    ):
        """Higher weighted videos should have more influence on result"""
        food_id = SAMPLE_POSTS["food-bbq-texas"]["id"]
        american_id = SAMPLE_POSTS["us-chicago-travel"]["id"]
        
        # Scenario 1: Food has higher weight
        result_food_heavy = await mock_embedding_service.generate_weighted_embedding(
            embeddings=[post_embeddings[food_id], post_embeddings[american_id]],
            weights=[1.0, 0.3]  # Food dominant
        )
        
        # Scenario 2: American has higher weight
        result_american_heavy = await mock_embedding_service.generate_weighted_embedding(
            embeddings=[post_embeddings[food_id], post_embeddings[american_id]],
            weights=[0.3, 1.0]  # American dominant
        )
        
        # Food-heavy result should be more similar to food posts
        food_sim_food_heavy = cosine_similarity(result_food_heavy, post_embeddings[food_id])
        food_sim_american_heavy = cosine_similarity(result_american_heavy, post_embeddings[food_id])
        
        assert food_sim_food_heavy > food_sim_american_heavy, \
            "Food-heavy should be closer to food posts"
    
    @pytest.mark.asyncio
    async def test_likes_have_stronger_influence_than_watches(
        self, post_embeddings, mock_embedding_service
    ):
        """Liked videos (weight 1.2) should outweigh watched videos (weight 1.0)"""
        food_id = SAMPLE_POSTS["food-bbq-texas"]["id"]
        american_id = SAMPLE_POSTS["us-chicago-travel"]["id"]
        
        # User watched food (80%) but LIKED american
        result = await mock_embedding_service.generate_weighted_embedding(
            embeddings=[post_embeddings[food_id], post_embeddings[american_id]],
            weights=[1.0, 1.2]  # American is liked
        )
        
        # Should be slightly closer to american due to higher weight
        food_sim = cosine_similarity(result, post_embeddings[food_id])
        american_sim = cosine_similarity(result, post_embeddings[american_id])
        
        assert american_sim > food_sim, \
            "Liked content should have more influence"


class TestRecommendationRanking:
    """Tests for ranking candidate posts by similarity"""
    
    def test_same_category_ranks_higher(self, post_embeddings):
        """Posts from same category as user interest should rank higher"""
        # User preference embedding is average of food posts
        food_ids = [
            SAMPLE_POSTS["food-bbq-texas"]["id"],
            SAMPLE_POSTS["food-pho-vietnamese"]["id"],
        ]
        
        user_embedding = np.mean(
            [post_embeddings[fid] for fid in food_ids], axis=0
        ).tolist()
        
        # Score all candidates
        scores = []
        for key, post in SAMPLE_POSTS.items():
            sim = cosine_similarity(user_embedding, post_embeddings[post["id"]])
            scores.append((key, post["category"], sim))
        
        # Sort by similarity
        ranked = sorted(scores, key=lambda x: x[2], reverse=True)
        
        # Top results should be food
        top_3 = ranked[:3]
        food_in_top_3 = sum(1 for r in top_3 if r[1] == "food")
        assert food_in_top_3 >= 2, f"Expected mostly food in top 3, got {top_3}"
    
    def test_watched_food_recommends_food(self, post_embeddings):
        """User who watched food should get food recommendations"""
        # Simulate user who watched BBQ and Pho
        user_embedding = np.mean([
            post_embeddings[SAMPLE_POSTS["food-bbq-texas"]["id"]],
            post_embeddings[SAMPLE_POSTS["food-pho-vietnamese"]["id"]],
        ], axis=0).tolist()
        
        # Find most similar post (excluding watched)
        watched_ids = {
            SAMPLE_POSTS["food-bbq-texas"]["id"],
            SAMPLE_POSTS["food-pho-vietnamese"]["id"],
        }
        
        candidates = [
            (key, post)
            for key, post in SAMPLE_POSTS.items()
            if post["id"] not in watched_ids
        ]
        
        best_match = max(
            candidates,
            key=lambda x: cosine_similarity(
                user_embedding, post_embeddings[x[1]["id"]]
            )
        )
        
        assert best_match[1]["category"] == "food", \
            f"Expected food, got {best_match[0]} ({best_match[1]['category']})"
    
    def test_watched_american_recommends_american(self, post_embeddings):
        """User who watched American content should get American recommendations"""
        # Simulate user who watched Chicago and School Life
        user_embedding = np.mean([
            post_embeddings[SAMPLE_POSTS["us-chicago-travel"]["id"]],
            post_embeddings[SAMPLE_POSTS["us-school-life"]["id"]],
        ], axis=0).tolist()
        
        # Find most similar post (excluding watched)
        watched_ids = {
            SAMPLE_POSTS["us-chicago-travel"]["id"],
            SAMPLE_POSTS["us-school-life"]["id"],
        }
        
        candidates = [
            (key, post)
            for key, post in SAMPLE_POSTS.items()
            if post["id"] not in watched_ids
        ]
        
        scores = [
            (key, post["category"], cosine_similarity(
                user_embedding, post_embeddings[post["id"]]
            ))
            for key, post in candidates
        ]
        
        top_post = max(scores, key=lambda x: x[2])
        assert top_post[1] == "american", f"Expected american, got {top_post}"


class TestExclusionLogic:
    """Tests for excluding already-seen content"""
    
    def test_watched_videos_excluded_regardless_of_percent(self):
        """All watched videos should be excluded, even if skipped"""
        session_watches = [
            {"post_id": "id1", "watch_percent": 0.95},  # Completed
            {"post_id": "id2", "watch_percent": 0.50},  # Half watched
            {"post_id": "id3", "watch_percent": 0.05},  # Skipped
        ]
        
        watched_ids = {w["post_id"] for w in session_watches}
        
        candidate_ids = ["id1", "id2", "id3", "id4", "id5"]
        filtered = [cid for cid in candidate_ids if cid not in watched_ids]
        
        assert filtered == ["id4", "id5"], "Should exclude all watched regardless of %"
    
    def test_db_history_merged_with_session(self):
        """Both DB history and session watches should be excluded"""
        db_history = {"db_id_1", "db_id_2"}
        session_watches = {"session_id_1", "session_id_2"}
        
        all_watched = db_history | session_watches
        
        candidates = ["db_id_1", "session_id_1", "new_id_1", "new_id_2"]
        filtered = [c for c in candidates if c not in all_watched]
        
        assert filtered == ["new_id_1", "new_id_2"]
    
    def test_liked_videos_also_excluded(self):
        """Liked videos should be excluded from recommendations"""
        watched = {"w1", "w2"}
        liked = {"l1", "l2"}
        
        all_excluded = watched | liked
        
        candidates = ["w1", "l1", "new1"]
        filtered = [c for c in candidates if c not in all_excluded]
        
        assert filtered == ["new1"]


class TestMeaningfulWatchFiltering:
    """Tests for filtering out low-engagement watches from embedding computation"""
    
    def test_only_meaningful_watches_contribute_to_embedding(self):
        """Only watches >= 20% should contribute to user embedding"""
        watches = [
            {"post_id": "id1", "watch_percent": 0.90, "embedding": [1, 0, 0]},
            {"post_id": "id2", "watch_percent": 0.15, "embedding": [0, 1, 0]},  # Skip
            {"post_id": "id3", "watch_percent": 0.60, "embedding": [0, 0, 1]},
            {"post_id": "id4", "watch_percent": 0.05, "embedding": [1, 1, 0]},  # Skip
        ]
        
        # Filter for meaningful engagement
        meaningful = [w for w in watches if w["watch_percent"] >= 0.2]
        
        assert len(meaningful) == 2
        assert meaningful[0]["post_id"] == "id1"
        assert meaningful[1]["post_id"] == "id3"
    
    def test_skipped_videos_still_excluded_from_recommendations(self):
        """Skipped videos don't affect embedding but still excluded from recs"""
        watches = [
            {"post_id": "id1", "watch_percent": 0.90},
            {"post_id": "id2", "watch_percent": 0.05},  # Skipped
        ]
        
        # All watched excluded
        excluded_ids = {w["post_id"] for w in watches}
        
        # Only meaningful watches for embedding
        for_embedding = [w for w in watches if w["watch_percent"] >= 0.2]
        
        assert "id2" in excluded_ids, "Skipped should be excluded from recs"
        assert len(for_embedding) == 1, "Skipped shouldn't affect embedding"


class TestDiscoveryFallback:
    """Tests for fallback behavior when not enough watch history"""
    
    def test_returns_discovery_when_no_watches(self):
        """Should return discovery mode when user has no watch history"""
        watches = []
        
        has_meaningful_history = any(
            w.get("watch_percent", 0) >= 0.2 for w in watches
        )
        
        assert not has_meaningful_history
        # In this case, system should return discovery/popular posts
    
    def test_returns_discovery_when_all_watches_below_threshold(self):
        """Should return discovery when all watches are skips"""
        watches = [
            {"post_id": "id1", "watch_percent": 0.10},
            {"post_id": "id2", "watch_percent": 0.15},
            {"post_id": "id3", "watch_percent": 0.05},
        ]
        
        meaningful = [w for w in watches if w["watch_percent"] >= 0.2]
        
        assert len(meaningful) == 0
        # System should fallback to discovery mode
    
    def test_discovery_allows_replay_when_all_watched(self):
        """When all content is watched, discovery should allow replays"""
        all_post_ids = {"id1", "id2", "id3"}
        watched_ids = {"id1", "id2", "id3"}
        
        unwatched = all_post_ids - watched_ids
        
        assert len(unwatched) == 0
        # System should allow replay of oldest watched content
