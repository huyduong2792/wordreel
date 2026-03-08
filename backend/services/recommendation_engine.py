"""
AI-powered recommendation engine using vector embeddings
"""
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from database.supabase_client import get_supabase, get_service_supabase
from services.embedding_service import EmbeddingService
import structlog

logger = structlog.get_logger()


class RecommendationEngine:
    """
    Generate unified session-based recommendations using watch percentages and likes.
    
    Strategy:
    1. Use watch completion % to determine interest level
    2. Use likes as strong positive signal (weight: 1.2)
    3. Compute weighted interest vector from watched + liked videos
    4. Use pgvector cosine similarity to find similar content
    5. Fall back to trending + new for cold start
    
    Watch percent weighting:
    - >= 80%: Strong interest (1.0)
    - 50-80%: Moderate interest (0.6)
    - 20-50%: Low interest (0.3)
    - < 20%: Skipped/disliked (0.0)
    
    Like weighting:
    - Liked: Very strong interest (1.2) - higher than 100% watch
    """
    
    # Like weight is higher than watch to prioritize explicit signals
    LIKE_WEIGHT = 1.2
    
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self._embedding_service = embedding_service
    
    @property
    def embedding_service(self) -> EmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service
    
    def _watch_percent_to_weight(self, watch_percent: float) -> float:
        """Convert watch percentage to interest weight"""
        if watch_percent >= 0.8:
            return 1.0  # Strong interest
        elif watch_percent >= 0.5:
            return 0.6  # Moderate interest
        elif watch_percent >= 0.2:
            return 0.3  # Low interest
        else:
            return 0.0  # Skipped/disliked
    
    async def load_user_watch_history(
        self,
        user_id: str,
        limit: int = 30
    ) -> List[Tuple[str, float]]:
        """
        Load user's watch history from database.
        
        Returns list of (post_id, watch_percent) tuples.
        """
        supabase = get_service_supabase()
        
        try:
            response = supabase.table("view_history").select(
                "post_id, watch_percent"
            ).eq("user_id", user_id).order(
                "updated_at", desc=True
            ).limit(limit).execute()
            
            return [
                (r["post_id"], r.get("watch_percent", 0.5))
                for r in response.data
            ]
            
        except Exception as e:
            logger.warning("Failed to load watch history", error=str(e))
            return []
    
    async def load_user_like_history(
        self,
        user_id: str,
        limit: int = 30
    ) -> List[str]:
        """
        Load user's like history from database.
        
        Returns list of post_ids that user has liked.
        """
        supabase = get_service_supabase()
        
        try:
            response = supabase.table("post_likes").select(
                "post_id"
            ).eq("user_id", user_id).order(
                "created_at", desc=True
            ).limit(limit).execute()
            
            return [r["post_id"] for r in response.data if r.get("post_id")]
            
        except Exception as e:
            logger.warning("Failed to load like history", error=str(e))
            return []
    
    async def get_all_watched_post_ids(self, user_id: str) -> List[str]:
        """
        Get ALL post IDs that user has ever watched.
        Used for exclusion from recommendations (not for embedding computation).
        
        Returns list of post_ids (no limit).
        """
        supabase = get_service_supabase()
        
        try:
            response = supabase.table("view_history").select(
                "post_id"
            ).eq("user_id", user_id).execute()
            
            return [r["post_id"] for r in response.data if r.get("post_id")]
            
        except Exception as e:
            logger.warning("Failed to get all watched post ids", error=str(e))
            return []
    
    async def get_watch_based_recommendations(
        self,
        session_watches: List[Tuple[str, float]],
        limit: int = 10,
        content_type: Optional[str] = None,
        additional_exclude_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> List[str]:
        """
        Get recommendations based on session watch history and likes (from DB).
        
        Args:
            session_watches: List of (post_id, watch_percent) tuples
            limit: Number of recommendations to return
            content_type: Optional filter by content type
            additional_exclude_ids: Additional post IDs to exclude (e.g., from DB history)
            user_id: User ID to load likes from DB (logged-in users only)
        
        Returns empty list if no meaningful signals - caller should handle discovery fallback.
        """
        supabase = get_service_supabase()
        
        # Load likes from DB for logged-in users
        user_likes = []
        if user_id:
            user_likes = await self.load_user_like_history(user_id, limit=30)
        
        try:
            # Check if we have any engagement signals
            has_watches = bool(session_watches)
            has_likes = bool(user_likes)
            
            if not has_watches and not has_likes:
                return []
            
            # Get ALL watched video IDs (to exclude from recommendations)
            all_watched_ids = [pid for pid, _ in session_watches] if session_watches else []
            
            # Merge with additional exclude IDs (e.g., full DB history)
            if additional_exclude_ids:
                all_watched_ids = list(set(all_watched_ids + additional_exclude_ids))
            
            # Filter to videos with meaningful watch (>= 20%)
            meaningful_watches = [
                (pid, pct) for pid, pct in session_watches
                if pct >= 0.2
            ] if session_watches else []
            
            # Combine post IDs from both watches and likes for embedding fetch
            watch_post_ids = [pid for pid, _ in meaningful_watches]
            all_signal_post_ids = list(set(watch_post_ids + user_likes))
            
            if not all_signal_post_ids:
                return []
            
            # Get embeddings for all signal posts (watches + likes)
            posts = supabase.table("posts").select(
                "id, embedding"
            ).in_("id", all_signal_post_ids).not_.is_("embedding", "null").execute()
            
            if not posts.data:
                return []
            
            # Create embedding map (parse string embeddings to list of floats)
            embedding_map = {}
            for p in posts.data:
                emb = p.get("embedding")
                if emb:
                    # Handle string embeddings from pgvector
                    if isinstance(emb, str):
                        import json
                        try:
                            emb = json.loads(emb)
                        except json.JSONDecodeError:
                            continue
                    embedding_map[p["id"]] = emb
            
            # Build weighted embeddings from both watches and likes
            weighted_embeddings = []
            weights = []
            processed_ids = set()  # Track to avoid double-counting
            
            # Add liked posts with high weight (1.2)
            for post_id in user_likes:
                if post_id in embedding_map and post_id not in processed_ids:
                    weighted_embeddings.append(embedding_map[post_id])
                    weights.append(self.LIKE_WEIGHT)
                    processed_ids.add(post_id)
            
            # Add watched posts with watch-percent-based weight
            for post_id, watch_percent in meaningful_watches:
                if post_id in embedding_map and post_id not in processed_ids:
                    weight = self._watch_percent_to_weight(watch_percent)
                    if weight > 0:
                        weighted_embeddings.append(embedding_map[post_id])
                        weights.append(weight)
                        processed_ids.add(post_id)
            
            if not weighted_embeddings:
                return []
            
            # Compute weighted user interest vector
            user_embedding = await self.embedding_service.generate_weighted_embedding(
                embeddings=weighted_embeddings,
                weights=weights
            )
            
            if not user_embedding:
                return []
            
            # Exclude ALL watched videos AND liked videos from recommendations
            exclude_ids = list(set(all_watched_ids + user_likes))
            
            # Query similar posts
            recommended_ids = await self._query_similar_posts(
                embedding=user_embedding,
                limit=limit,
                exclude_ids=exclude_ids,
                content_type=content_type
            )
            
            logger.info(
                "Recommendations generated",
                session_watches=len(session_watches) if session_watches else 0,
                user_likes=len(user_likes),
                meaningful_watches=len(meaningful_watches),
                result_count=len(recommended_ids)
            )
            
            return recommended_ids[:limit]
            
        except Exception as e:
            logger.error("Watch-based recommendations failed", error=str(e))
            return []
    
    async def _query_similar_posts(
        self,
        embedding: List[float],
        limit: int,
        exclude_ids: List[str],
        content_type: Optional[str] = None
    ) -> List[str]:
        """
        Query posts similar to the embedding using pgvector.
        
        This uses the <=> operator for cosine distance.
        Lower distance = more similar.
        """
        supabase = get_service_supabase()
        
        try:
            # Use Supabase RPC for vector similarity search
            params = {
                "query_embedding": embedding,
                "match_count": limit + len(exclude_ids),
                "exclude_ids": exclude_ids
            }
            
            if content_type:
                params["filter_content_type"] = content_type
            
            response = supabase.rpc(
                "match_posts_by_embedding",
                params
            ).execute()
            
            if response.data:
                return [p["id"] for p in response.data][:limit]
            
            return []
            
        except Exception as e:
            logger.warning("Vector search failed, using fallback", error=str(e))
            # Fallback: just return recent posts
            return await self._get_recent_posts(limit, exclude_ids, content_type)
    
    async def _get_recent_posts(
        self,
        limit: int,
        exclude_ids: List[str],
        content_type: Optional[str] = None
    ) -> List[str]:
        """Fallback: get recent posts"""
        supabase = get_service_supabase()
        
        try:
            query = supabase.table("posts").select("id").eq(
                "status", "ready"
            ).order("created_at", desc=True).limit(limit + len(exclude_ids))
            
            if content_type:
                query = query.eq("content_type", content_type)
            
            response = query.execute()
            
            return [
                p["id"] for p in response.data
                if p["id"] not in exclude_ids
            ][:limit]
            
        except Exception:
            return []
    
    async def get_trending_videos(
        self,
        limit: int = 10,
        exclude_ids: Optional[List[str]] = None
    ) -> List[str]:
        """Get trending posts based on recent engagement"""
        supabase = get_service_supabase()
        exclude_ids = exclude_ids or []
        
        try:
            # Get posts with recent engagement
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            
            response = supabase.table("posts").select(
                "id, views_count, likes_count, created_at"
            ).eq("status", "ready").gte(
                "created_at", week_ago
            ).order(
                "views_count", desc=True
            ).order(
                "likes_count", desc=True
            ).limit(limit * 3).execute()
            
            # Score by recency and popularity
            scored = []
            now = datetime.now()
            
            for post in response.data:
                if post["id"] in exclude_ids:
                    continue
                
                created_at = datetime.fromisoformat(
                    post["created_at"].replace("Z", "+00:00").replace("+00:00", "")
                )
                age_days = (now - created_at).days
                
                # Recency factor
                recency = max(0, 1 - (age_days / 7))
                
                # Engagement score
                engagement = (
                    post.get("views_count", 0) * 0.5 +
                    post.get("likes_count", 0) * 10
                )
                
                score = engagement * (0.6 + recency * 0.4)
                scored.append((post["id"], score))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            return [p[0] for p in scored[:limit]]
            
        except Exception as e:
            logger.error("Failed to get trending", error=str(e))
            # Ultimate fallback: just get any ready posts
            response = supabase.table("posts").select("id").eq(
                "status", "ready"
            ).limit(limit).execute()
            return [p["id"] for p in response.data]
    
    async def get_similar_videos(
        self,
        video_id: str,
        limit: int = 10
    ) -> List[str]:
        """Get posts similar to a specific post"""
        supabase = get_service_supabase()
        
        try:
            # Get post embedding
            post = supabase.table("posts").select(
                "embedding, content_type"
            ).eq("id", video_id).execute()
            
            if not post.data or not post.data[0].get("embedding"):
                # Fallback to tag-based
                return await self._get_similar_by_tags(video_id, limit)
            
            embedding = post.data[0]["embedding"]
            content_type = post.data[0].get("content_type")
            
            # Query similar posts (optionally filter by same content type)
            return await self._query_similar_posts(
                embedding=embedding,
                limit=limit,
                exclude_ids=[video_id],
                content_type=None  # Set to content_type to match same type only
            )
            
        except Exception as e:
            logger.error("Similar posts failed", error=str(e))
            return []
    
    async def _get_similar_by_tags(
        self,
        post_id: str,
        limit: int
    ) -> List[str]:
        """Fallback: find similar posts by tags"""
        supabase = get_service_supabase()
        
        try:
            # Get post tags
            post = supabase.table("posts").select("tags").eq(
                "id", post_id
            ).execute()
            
            if not post.data or not post.data[0].get("tags"):
                return []
            
            tags = post.data[0]["tags"]
            
            # Find posts with overlapping tags
            response = supabase.table("posts").select("id").eq(
                "status", "ready"
            ).neq("id", post_id).contains(
                "tags", tags
            ).limit(limit).execute()
            
            return [p["id"] for p in response.data]
            
        except Exception:
            return []

    async def get_discovery_feed(
        self,
        limit: int = 10,
        difficulty: Optional[str] = "beginner",
        exclude_ids: Optional[List[str]] = None,
        allow_replay: bool = True
    ) -> List[str]:
        """
        Get discovery feed for new/anonymous users.
        
        Mix of:
        - 50% trending content (social proof)
        - 30% new content (freshness)
        - 20% curated beginner-friendly content
        
        Prioritizes beginner difficulty for new users to ensure good first experience.
        
        If allow_replay=True and all videos are watched, will return videos again
        (ignoring exclude_ids) to provide continuous content.
        """
        supabase = get_service_supabase()
        exclude_ids = exclude_ids or []
        
        try:
            result_ids = []
            
            # 50% trending
            trending_limit = limit // 2
            trending = await self.get_trending_videos(
                limit=trending_limit,
                exclude_ids=exclude_ids
            )
            result_ids.extend(trending)
            
            # 30% new content (last 48 hours)
            new_limit = limit * 3 // 10
            from datetime import datetime, timedelta
            two_days_ago = (datetime.now() - timedelta(hours=48)).isoformat()
            
            new_query = supabase.table("posts").select("id").eq(
                "status", "ready"
            ).gte("created_at", two_days_ago).order(
                "created_at", desc=True
            ).limit(new_limit + len(exclude_ids) + len(result_ids))
            
            if difficulty:
                new_query = new_query.eq("difficulty_level", difficulty)
            
            new_response = new_query.execute()
            new_ids = [
                p["id"] for p in new_response.data 
                if p["id"] not in exclude_ids and p["id"] not in result_ids
            ][:new_limit]
            result_ids.extend(new_ids)
            
            # 20% curated (high engagement + beginner friendly)
            remaining = limit - len(result_ids)
            if remaining > 0:
                curated_query = supabase.table("posts").select("id").eq(
                    "status", "ready"
                ).eq("difficulty_level", difficulty or "beginner").order(
                    "likes_count", desc=True
                ).limit(remaining + len(exclude_ids) + len(result_ids))
                
                curated_response = curated_query.execute()
                curated_ids = [
                    p["id"] for p in curated_response.data
                    if p["id"] not in exclude_ids and p["id"] not in result_ids
                ][:remaining]
                result_ids.extend(curated_ids)
            
            # If not enough results and allow_replay, ignore exclude_ids and get trending again
            if len(result_ids) < limit and allow_replay:
                logger.info(
                    "Not enough unwatched videos, allowing replay",
                    current_count=len(result_ids),
                    requested=limit,
                    exclude_count=len(exclude_ids)
                )
                # Get more trending videos without exclusion (allow re-watching)
                replay_needed = limit - len(result_ids)
                replay_trending = await self.get_trending_videos(
                    limit=replay_needed,
                    exclude_ids=result_ids  # Only exclude what we already have in this result
                )
                result_ids.extend(replay_trending)
                
                # If still not enough, get any ready posts without any exclusion
                if len(result_ids) < limit:
                    any_needed = limit - len(result_ids)
                    any_posts = supabase.table("posts").select("id").eq(
                        "status", "ready"
                    ).order("created_at", desc=True).limit(any_needed + len(result_ids)).execute()
                    
                    any_ids = [
                        p["id"] for p in any_posts.data
                        if p["id"] not in result_ids
                    ][:any_needed]
                    result_ids.extend(any_ids)
            
            logger.info(
                "Discovery feed generated",
                trending=len(trending),
                new=len(new_ids),
                curated=len(result_ids) - len(trending) - len(new_ids),
                difficulty=difficulty,
                allow_replay=allow_replay
            )
            
            return result_ids[:limit]
            
        except Exception as e:
            logger.error("Discovery feed failed", error=str(e))
            return await self._get_recent_posts(limit, exclude_ids, None)

    async def _filter_by_difficulty(
        self,
        post_ids: List[str],
        difficulty: str
    ) -> List[str]:
        """Filter posts by difficulty level"""
        if not post_ids:
            return []
            
        supabase = get_service_supabase()
        
        try:
            response = supabase.table("posts").select("id").in_(
                "id", post_ids
            ).eq("difficulty_level", difficulty).execute()
            
            # Preserve original order
            filtered_ids = {p["id"] for p in response.data}
            return [pid for pid in post_ids if pid in filtered_ids]
            
        except Exception:
            return post_ids  # Return unfiltered on error
