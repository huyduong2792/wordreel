"""
Redis client for session management and recommendation caching
"""
import json
import redis
from typing import List, Optional, Dict, Any, Tuple
from datetime import timedelta
from config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()

# Session TTL: 7 days for logged-in, 24 hours for anonymous
SESSION_TTL_LOGGED_IN = timedelta(days=7)
SESSION_TTL_ANONYMOUS = timedelta(hours=24)

# Recommendation cache TTL: 2 minutes
RECOMMENDATION_CACHE_TTL = timedelta(minutes=2)

# Similar posts cache TTL: 10 minutes (content doesn't change often)
SIMILAR_POSTS_CACHE_TTL = timedelta(minutes=10)


class RedisSessionClient:
    """
    Redis client for managing user sessions and recommendation cache.
    
    Keys structure:
    - session:{session_id}:watches -> List of watch items [{post_id, watch_percent, timestamp}]
    - session:{session_id}:user -> User info {user_id, logged_in}
    - session:{session_id}:recommendations -> Cached recommendations [post_ids]
    - pending_syncs -> Set of session_ids that need DB sync
    """
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
    
    @property
    def client(self) -> redis.Redis:
        """Lazy-load Redis client"""
        if self._client is None:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True
            )
        return self._client
    
    def _watches_key(self, session_id: str) -> str:
        return f"session:{session_id}:watches"
    
    def _user_key(self, session_id: str) -> str:
        return f"session:{session_id}:user"
    
    def _recommendations_key(self, session_id: str) -> str:
        return f"session:{session_id}:recommendations"
    
    def _pending_syncs_key(self) -> str:
        return "pending_syncs"
    
    # ==================== Session Management ====================
    
    def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        initial_watches: Optional[List[Dict]] = None
    ) -> bool:
        """
        Create or update a session.
        
        Args:
            session_id: Unique session identifier
            user_id: User ID if logged in, None for anonymous
            initial_watches: Initial watch history (e.g., from DB for logged-in users)
        """
        try:
            ttl = SESSION_TTL_LOGGED_IN if user_id else SESSION_TTL_ANONYMOUS
            
            # Store user info
            user_data = {
                "user_id": user_id or "",
                "logged_in": bool(user_id)
            }
            self.client.set(
                self._user_key(session_id),
                json.dumps(user_data),
                ex=int(ttl.total_seconds())
            )
            
            # Initialize watches if provided
            if initial_watches:
                watches_key = self._watches_key(session_id)
                self.client.delete(watches_key)
                for watch in initial_watches:
                    self.client.rpush(watches_key, json.dumps(watch))
                self.client.expire(watches_key, int(ttl.total_seconds()))
            
            logger.info(
                "Session created",
                session_id=session_id,
                user_id=user_id,
                initial_watches_count=len(initial_watches) if initial_watches else 0
            )
            return True
            
        except Exception as e:
            logger.error("Failed to create session", error=str(e))
            return False
    
    def get_session_user(self, session_id: str) -> Optional[Dict]:
        """Get session user info"""
        try:
            data = self.client.get(self._user_key(session_id))
            return json.loads(data) if data else None
        except Exception:
            return None
    
    def extend_session_ttl(self, session_id: str, user_id: Optional[str] = None):
        """Extend session TTL on activity"""
        try:
            ttl = SESSION_TTL_LOGGED_IN if user_id else SESSION_TTL_ANONYMOUS
            ttl_seconds = int(ttl.total_seconds())
            
            self.client.expire(self._watches_key(session_id), ttl_seconds)
            self.client.expire(self._user_key(session_id), ttl_seconds)
            # NOTE: Do NOT extend recommendations TTL - it should stay at 5 minutes
            # to ensure fresh recommendations are computed regularly
        except Exception as e:
            logger.warning("Failed to extend session TTL", error=str(e))
    
    # ==================== Watch Tracking ====================
    
    def track_watch(
        self,
        session_id: str,
        post_id: str,
        watch_percent: float,
        watch_duration: float,
        event_type: str = "progress"  # progress, pause, finish, seek
    ) -> bool:
        """
        Track a watch event.
        
        Args:
            session_id: Session identifier
            post_id: Video post ID
            watch_percent: Completion percentage (0.0 to 1.0)
            watch_duration: Seconds watched
            event_type: Type of event (progress, pause, finish, seek)
        """
        try:
            import time
            
            watches_key = self._watches_key(session_id)
            
            # Get existing watches to update or append
            existing_watches = self.get_session_watches(session_id)
            
            # Find existing watch for this post
            watch_data = {
                "post_id": post_id,
                "watch_percent": watch_percent,
                "watch_duration": watch_duration,
                "event_type": event_type,
                "timestamp": time.time()
            }
            
            # Update existing or append new
            updated = False
            for i, watch in enumerate(existing_watches):
                if watch.get("post_id") == post_id:
                    # Keep higher watch percent
                    watch_data["watch_percent"] = max(
                        watch.get("watch_percent", 0),
                        watch_percent
                    )
                    watch_data["watch_duration"] = max(
                        watch.get("watch_duration", 0),
                        watch_duration
                    )
                    existing_watches[i] = watch_data
                    updated = True
                    break
            
            if not updated:
                existing_watches.append(watch_data)
            
            # Keep last 50 watches
            existing_watches = existing_watches[-50:]
            
            # Save back to Redis
            self.client.delete(watches_key)
            for watch in existing_watches:
                self.client.rpush(watches_key, json.dumps(watch))
            
            # Get user info for TTL
            user_info = self.get_session_user(session_id)
            ttl = SESSION_TTL_LOGGED_IN if user_info and user_info.get("logged_in") else SESSION_TTL_ANONYMOUS
            self.client.expire(watches_key, int(ttl.total_seconds()))
            
            # Mark session for DB sync (for logged-in users)
            if user_info and user_info.get("logged_in"):
                self.client.sadd(self._pending_syncs_key(), session_id)
            
            # Remove post from cached recommendations immediately on 'start'
            # This prevents the video from appearing again in the feed
            if event_type == "start":
                self.remove_post_from_recommendations(session_id, post_id)
            
            logger.debug(
                "Watch tracked",
                session_id=session_id,
                post_id=post_id,
                watch_percent=watch_percent,
                event_type=event_type
            )
            return True
            
        except Exception as e:
            logger.error("Failed to track watch", error=str(e))
            return False
    
    def get_session_watches(self, session_id: str) -> List[Dict]:
        """Get all watches for a session"""
        try:
            watches_key = self._watches_key(session_id)
            raw_watches = self.client.lrange(watches_key, 0, -1)
            return [json.loads(w) for w in raw_watches]
        except Exception as e:
            logger.warning("Failed to get session watches", error=str(e))
            return []
    
    def get_session_watches_before(self, session_id: str, before_timestamp: float) -> Tuple[List[Dict], bool]:
        """
        Get watches that occurred before a specific timestamp.
        
        Used for safe DB sync to avoid race conditions:
        - Only syncs watches that existed before sync started
        - New watches added during sync are preserved for next cycle
        
        Args:
            session_id: Session identifier
            before_timestamp: Only return watches with timestamp < this value
        
        Returns:
            Tuple of (watches_to_sync, has_remaining)
            - watches_to_sync: Watches that should be synced
            - has_remaining: True if there are newer watches left unsent
        """
        try:
            all_watches = self.get_session_watches(session_id)
            
            watches_to_sync = []
            has_remaining = False
            
            for watch in all_watches:
                watch_ts = watch.get("timestamp", 0)
                if watch_ts < before_timestamp:
                    watches_to_sync.append(watch)
                else:
                    has_remaining = True
            
            return watches_to_sync, has_remaining
        except Exception as e:
            logger.warning("Failed to get session watches before timestamp", error=str(e))
            return [], False
    
    # ==================== Recommendations Cache ====================
    
    def cache_recommendations(
        self,
        session_id: str,
        post_ids: List[str],
        recommendation_type: str = "session"
    ) -> bool:
        """
        Cache recommendations for a session.
        
        Args:
            session_id: Session identifier
            post_ids: List of recommended post IDs
            recommendation_type: Type of recommendation (session/discovery)
        """
        try:
            rec_key = self._recommendations_key(session_id)
            data = {
                "post_ids": post_ids,
                "type": recommendation_type,
                "cached_at": __import__("time").time()
            }
            self.client.set(
                rec_key,
                json.dumps(data),
                ex=int(RECOMMENDATION_CACHE_TTL.total_seconds())
            )
            return True
        except Exception as e:
            logger.warning("Failed to cache recommendations", error=str(e))
            return False
    
    def get_cached_recommendations(self, session_id: str) -> Optional[Dict]:
        """Get cached recommendations if still valid"""
        try:
            rec_key = self._recommendations_key(session_id)
            data = self.client.get(rec_key)
            return json.loads(data) if data else None
        except Exception:
            return None
    
    def invalidate_recommendations(self, session_id: str):
        """Invalidate cached recommendations (e.g., after new watch)"""
        try:
            self.client.delete(self._recommendations_key(session_id))
        except Exception:
            pass
    
    def remove_post_from_recommendations(self, session_id: str, post_id: str) -> bool:
        """
        Remove a specific post from cached recommendations.
        Called when user starts watching a video to prevent it from appearing again.
        
        Args:
            session_id: Session identifier
            post_id: Post ID to remove from recommendations
            
        Returns:
            True if removed, False if not found or error
        """
        try:
            rec_key = self._recommendations_key(session_id)
            data = self.client.get(rec_key)
            if not data:
                return False
            
            cached = json.loads(data)
            post_ids = cached.get("post_ids", [])
            
            if post_id not in post_ids:
                return False
            
            # Remove the post from recommendations
            post_ids = [pid for pid in post_ids if pid != post_id]
            cached["post_ids"] = post_ids
            
            # Get remaining TTL to preserve it
            ttl = self.client.ttl(rec_key)
            if ttl > 0:
                self.client.set(rec_key, json.dumps(cached), ex=ttl)
            else:
                self.client.set(
                    rec_key,
                    json.dumps(cached),
                    ex=int(RECOMMENDATION_CACHE_TTL.total_seconds())
                )
            
            logger.debug(
                "Removed post from recommendations",
                session_id=session_id,
                post_id=post_id,
                remaining_count=len(post_ids)
            )
            return True
            
        except Exception as e:
            logger.warning("Failed to remove post from recommendations", error=str(e))
            return False
    
    # ==================== Pending Syncs (for worker) ====================
    
    # ==================== Similar Posts Cache ====================
    
    def _similar_posts_key(self, post_id: str, limit: int) -> str:
        """Key for caching similar posts"""
        return f"similar:{post_id}:limit:{limit}"
    
    def cache_similar_posts(
        self,
        post_id: str,
        similar_ids: List[str],
        limit: int
    ) -> bool:
        """
        Cache similar posts for a specific post.
        
        Args:
            post_id: The post ID to cache similar posts for
            similar_ids: List of similar post IDs
            limit: The limit used for the query (part of cache key)
        """
        try:
            cache_key = self._similar_posts_key(post_id, limit)
            data = {
                "similar_ids": similar_ids,
                "cached_at": __import__("time").time()
            }
            self.client.set(
                cache_key,
                json.dumps(data),
                ex=int(SIMILAR_POSTS_CACHE_TTL.total_seconds())
            )
            logger.debug(
                "Cached similar posts",
                post_id=post_id,
                count=len(similar_ids),
                limit=limit
            )
            return True
        except Exception as e:
            logger.warning("Failed to cache similar posts", error=str(e))
            return False
    
    def get_cached_similar_posts(self, post_id: str, limit: int) -> Optional[List[str]]:
        """
        Get cached similar posts if still valid.
        
        Args:
            post_id: The post ID to get similar posts for
            limit: The limit (must match cache key)
            
        Returns:
            List of similar post IDs if cached, None otherwise
        """
        try:
            cache_key = self._similar_posts_key(post_id, limit)
            data = self.client.get(cache_key)
            if data:
                cached = json.loads(data)
                return cached.get("similar_ids")
            return None
        except Exception:
            return None

    def get_pending_sync_sessions(self, limit: int = 100) -> List[str]:
        """Get sessions that need to be synced to DB"""
        try:
            return list(self.client.srandmember(self._pending_syncs_key(), limit) or [])
        except Exception:
            return []
    
    def mark_session_synced(self, session_id: str, has_remaining: bool = False):
        """
        Remove session from pending sync set.
        
        Args:
            session_id: Session identifier
            has_remaining: If True, re-add to pending_syncs for next cycle
                          (used when newer watches exist that weren't synced)
        """
        try:
            self.client.srem(self._pending_syncs_key(), session_id)
            if has_remaining:
                # Re-add for next sync cycle
                self.client.sadd(self._pending_syncs_key(), session_id)
        except Exception:
            pass
    
    def get_all_sessions_for_recommendations(self, limit: int = 100) -> List[str]:
        """Get all active sessions that might need recommendation refresh"""
        try:
            # Get all session keys (both watches and user keys)
            # This captures:
            # 1. Sessions with watches (session:*:watches)
            # 2. Logged-in users without watches (session:*:user) - they may have likes
            cursor = 0
            session_ids = set()
            
            # Scan for sessions with watches
            while len(session_ids) < limit:
                cursor, keys = self.client.scan(cursor, match="session:*:watches", count=100)
                for key in keys:
                    session_id = key.split(":")[1]
                    session_ids.add(session_id)
                if cursor == 0:
                    break
            
            # Also scan for user keys (logged-in users may have likes but no watches)
            cursor = 0
            while len(session_ids) < limit:
                cursor, keys = self.client.scan(cursor, match="session:*:user", count=100)
                for key in keys:
                    session_id = key.split(":")[1]
                    # Only add if user is logged in (has user_id)
                    user_info = self.get_session_user(session_id)
                    if user_info and user_info.get("logged_in"):
                        session_ids.add(session_id)
                if cursor == 0:
                    break
            
            return list(session_ids)[:limit]
        except Exception:
            return []

    # ==================== Rate Limiting ====================
    
    def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int]:
        """
        Check if action is rate limited using sliding window.
        
        Args:
            key: Unique key for the rate limit (e.g., "comment:{user_id}")
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        try:
            rate_key = f"ratelimit:{key}"
            current = self.client.incr(rate_key)
            
            if current == 1:
                # First request, set expiry
                self.client.expire(rate_key, window_seconds)
            
            remaining = max(0, max_requests - current)
            is_allowed = current <= max_requests
            
            return is_allowed, remaining
        except Exception as e:
            logger.warning("Rate limit check failed", error=str(e))
            # Fail open - allow request if Redis is down
            return True, max_requests


# Singleton instance
_redis_client: Optional[RedisSessionClient] = None


def get_redis_session_client() -> RedisSessionClient:
    """Get or create Redis session client singleton"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisSessionClient()
    return _redis_client
