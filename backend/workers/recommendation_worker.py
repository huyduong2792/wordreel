"""
Recommendation Worker - Standalone service for background processing

This worker:
1. Syncs watch history from Redis to PostgreSQL (for logged-in users)
2. Pre-computes recommendations for active sessions
3. Uses version tracking to prevent race conditions (stale cache)
4. Uses DB watch history to improve recommendation quality for logged-in users

Run: python -m workers.recommendation_worker
"""
import asyncio
import time
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import structlog

from services.redis_client import get_redis_session_client
from services.container import get_recommendation_engine
from database.supabase_client import get_service_supabase

logger = structlog.get_logger()

# Worker configuration
SYNC_INTERVAL = 60  # Sync to DB every 60 seconds
RECOMMENDATION_INTERVAL = 30  # Refresh recommendations every 30 seconds
BATCH_SIZE = 50  # Process 50 sessions per batch


class RecommendationWorker:
    """
    Background worker for recommendation system maintenance.
    """
    
    def __init__(self):
        self.redis_client = get_redis_session_client()
        self.recommendation_engine = get_recommendation_engine()
        self.running = False
    
    async def start(self):
        """Start the worker"""
        self.running = True
        logger.info("Recommendation worker started")
        
        # Run both tasks concurrently
        await asyncio.gather(
            self._sync_loop(),
            self._recommendation_loop()
        )
    
    def stop(self):
        """Stop the worker"""
        self.running = False
        logger.info("Recommendation worker stopping")
    
    # ==================== Database Sync ====================
    
    async def _sync_loop(self):
        """Main loop for syncing Redis data to PostgreSQL"""
        while self.running:
            try:
                await self._sync_pending_sessions()
                await asyncio.sleep(SYNC_INTERVAL)
            except Exception as e:
                logger.error("Sync loop error", error=str(e))
                await asyncio.sleep(10)
    
    async def _sync_pending_sessions(self):
        """Sync pending sessions to database"""
        import time
        
        try:
            # Get sessions that need syncing
            pending_sessions = self.redis_client.get_pending_sync_sessions(limit=BATCH_SIZE)
            
            if not pending_sessions:
                return
            
            logger.info(f"Syncing {len(pending_sessions)} sessions to database")
            
            # Record sync start time BEFORE reading any watches
            # This prevents race condition: only sync watches that existed before this point
            sync_start_time = time.time()
            
            supabase = get_service_supabase()
            synced_count = 0
            
            for session_id in pending_sessions:
                try:
                    # Get session user info
                    user_info = self.redis_client.get_session_user(session_id)
                    
                    if not user_info or not user_info.get("logged_in"):
                        # Skip anonymous sessions (no DB sync needed)
                        self.redis_client.mark_session_synced(session_id)
                        continue
                    
                    user_id = user_info.get("user_id")
                    if not user_id:
                        continue
                    
                    # Get only watches that occurred BEFORE sync started
                    # This prevents losing watches added during sync processing
                    watches, has_remaining = self.redis_client.get_session_watches_before(
                        session_id, 
                        before_timestamp=sync_start_time
                    )
                    
                    if not watches:
                        # No watches to sync, but check if there are newer ones
                        self.redis_client.mark_session_synced(session_id, has_remaining=has_remaining)
                        continue
                    
                    # Batch upsert to database
                    for watch in watches:
                        post_id = watch.get("post_id")
                        watch_percent = watch.get("watch_percent", 0)
                        watch_duration = watch.get("watch_duration", 0)
                        
                        if not post_id:
                            continue
                        
                        # Check if exists
                        existing = supabase.table("view_history").select("id, watch_percent").eq(
                            "user_id", user_id
                        ).eq("post_id", post_id).execute()
                        
                        if existing.data:
                            # Update only if new watch_percent is higher
                            current_percent = existing.data[0].get("watch_percent", 0) or 0
                            if watch_percent > current_percent:
                                supabase.table("view_history").update({
                                    "view_duration": watch_duration,
                                    "watch_percent": watch_percent,
                                    "updated_at": datetime.now().isoformat()
                                }).eq("id", existing.data[0]["id"]).execute()
                        else:
                            # Insert new record
                            supabase.table("view_history").insert({
                                "user_id": user_id,
                                "post_id": post_id,
                                "view_duration": watch_duration,
                                "watch_percent": watch_percent,
                                "completed": watch_percent >= 0.9
                            }).execute()
                    
                    # Mark synced, but re-add to pending if there are newer watches
                    self.redis_client.mark_session_synced(session_id, has_remaining=has_remaining)
                    synced_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to sync session {session_id}", error=str(e))
            
            logger.info(f"Synced {synced_count} sessions to database")
            
        except Exception as e:
            logger.error("Failed to sync pending sessions", error=str(e))
    
    async def _compute_recommendations_for_session(self, session_id: str) -> bool:
        """
        Compute recommendations for a single session.
        Used by both priority and regular recommendation loops.
        
        Returns True if recommendations were successfully computed and cached.
        """
        try:
            # Get watches for this session
            watches = self.redis_client.get_session_watches(session_id)
            
            # Get user info to check if logged in
            user_info = self.redis_client.get_session_user(session_id)
            user_id = user_info.get("user_id") if user_info else None
            
            if not watches and not user_id:
                # No watches and anonymous user - nothing to compute
                return False
            
            # Convert watches to tuples
            session_watches = [
                (w["post_id"], w.get("watch_percent", 0.5))
                for w in watches
            ] if watches else []
            
            # Track original session IDs (before merging with DB history)
            current_session_ids = [w[0] for w in session_watches]
            
            # For logged-in users: get full exclusion list and enhance with recent watches
            all_db_watched_ids = []
            if user_id:
                # Get ALL watched post IDs for exclusion (no limit)
                all_db_watched_ids = await self.recommendation_engine.get_all_watched_post_ids(user_id)
                
                # Get recent watches for embedding computation (limited)
                db_watches = await self.recommendation_engine.load_user_watch_history(
                    user_id=user_id,
                    limit=50
                )
                # Merge DB watches (lower priority than session)
                session_post_ids = {w[0] for w in session_watches}
                for post_id, percent in db_watches:
                    if post_id not in session_post_ids:
                        session_watches.append((post_id, percent * 0.8))  # Decay older watches
            
            # Compute recommendations (likes loaded from DB inside engine for logged-in users)
            post_ids = await self.recommendation_engine.get_watch_based_recommendations(
                session_watches=session_watches,
                limit=30,  # Pre-compute 30 recommendations
                additional_exclude_ids=all_db_watched_ids,
                user_id=user_id  # Engine loads likes from DB for this user
            )
            
            if post_ids:
                # Cache recommendations
                cached = self.redis_client.cache_recommendations(
                    session_id=session_id,
                    post_ids=post_ids,
                    recommendation_type="session"
                )
                return cached
            
            return False
            
        except Exception as e:
            logger.warning(f"Failed to compute recommendations for session {session_id}", error=str(e))
            return False
    
    # ==================== Recommendation Pre-computation ====================
    
    async def _recommendation_loop(self):
        """
        Slow loop for pre-computing recommendations for all active sessions.
        Runs every 30 seconds.
        """
        while self.running:
            try:
                await self._refresh_recommendations()
                await asyncio.sleep(RECOMMENDATION_INTERVAL)
            except Exception as e:
                logger.error("Recommendation loop error", error=str(e))
                await asyncio.sleep(10)
    
    async def _refresh_recommendations(self):
        """Pre-compute recommendations for active sessions"""
        try:
            # Get active sessions
            sessions = self.redis_client.get_all_sessions_for_recommendations(limit=BATCH_SIZE)
            
            if not sessions:
                return
            
            refreshed_count = 0
            
            for session_id in sessions:
                try:
                    # Check if recommendations are already cached and fresh
                    cached = self.redis_client.get_cached_recommendations(session_id)
                    if cached:
                        # Skip if already cached (TTL handles freshness)
                        continue
                    
                    # Use shared computation method
                    success = await self._compute_recommendations_for_session(session_id)
                    
                    if success:
                        refreshed_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to refresh recommendations for {session_id}", error=str(e))
            
            if refreshed_count > 0:
                logger.info(f"Refreshed recommendations for {refreshed_count} sessions")
            
        except Exception as e:
            logger.error("Failed to refresh recommendations", error=str(e))


async def main():
    """Entry point for the worker"""
    worker = RecommendationWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        worker.stop()
        logger.info("Worker stopped by user")


if __name__ == "__main__":
    asyncio.run(main())
