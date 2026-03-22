"""
Recommendation API endpoints - Redis session-based recommendations
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Query, Body, Header
from pydantic import BaseModel
from supabase import Client
from models.schemas import PostResponse, PostStatus, ContentType
from database.supabase_client import get_supabase, get_service_supabase
from database.utils import transform_post_data
from auth.utils import get_current_user, get_current_user_optional
from services.container import get_recommendation_engine
from services.redis_client import get_redis_session_client, RedisSessionClient
from services.recommendation_engine import RecommendationEngine
import uuid

router = APIRouter()


class WatchEventRequest(BaseModel):
    """Track video watch event"""
    post_id: str
    watch_percent: float  # 0.0 to 1.0
    watch_duration: float  # seconds watched
    event_type: str = "progress"  # progress, pause, finish, seek


class SessionInitRequest(BaseModel):
    """Initialize session request"""
    existing_session_id: Optional[str] = None


@router.post("/session/init")
async def init_session(
    request: SessionInitRequest = Body(default=SessionInitRequest()),
    current_user = Depends(get_current_user_optional),
    redis_client: RedisSessionClient = Depends(get_redis_session_client),
    recommendation_engine: RecommendationEngine = Depends(get_recommendation_engine)
):
    """
    Initialize a new session or validate existing session.
    
    Creates a Redis session and returns session_id.
    For logged-in users, loads watch history from DB into Redis.
    
    **Request:**
    ```json
    {
        "existing_session_id": "optional-uuid-from-localstorage"
    }
    ```
    
    **Returns:**
    ```json
    {
        "session_id": "uuid",
        "is_new": true,
        "user_type": "logged_in" | "anonymous",
        "watches_count": 5
    }
    ```
    """
    try:
        user_id = current_user.id if current_user else None
        
        # Check if existing session is valid
        if request.existing_session_id:
            existing_user = redis_client.get_session_user(request.existing_session_id)
            if existing_user:
                # Session exists and is valid
                redis_client.extend_session_ttl(request.existing_session_id, user_id)
                
                # If user just logged in, update session with their user_id
                if user_id and not existing_user.get("logged_in"):
                    # Merge session with user's DB history
                    db_watches = await recommendation_engine.load_user_watch_history(
                        user_id=user_id,
                        limit=30
                    )
                    existing_watches = redis_client.get_session_watches(request.existing_session_id)
                    existing_post_ids = {w["post_id"] for w in existing_watches}
                    
                    # Add DB watches that aren't in session
                    for post_id, percent in db_watches:
                        if post_id not in existing_post_ids:
                            redis_client.track_watch(
                                session_id=request.existing_session_id,
                                post_id=post_id,
                                watch_percent=percent,
                                watch_duration=0,
                                event_type="history"
                            )
                    
                    # Update user info
                    redis_client.create_session(
                        session_id=request.existing_session_id,
                        user_id=user_id,
                        initial_watches=None  # Keep existing watches
                    )
                
                watches = redis_client.get_session_watches(request.existing_session_id)
                return {
                    "session_id": request.existing_session_id,
                    "is_new": False,
                    "user_type": "logged_in" if user_id else "anonymous",
                    "watches_count": len(watches)
                }
        
        # Create new session
        session_id = str(uuid.uuid4())
        
        # For logged-in users, load watch history from DB
        initial_watches = []
        if user_id:
            db_watches = await recommendation_engine.load_user_watch_history(
                user_id=user_id,
                limit=30
            )
            initial_watches = [
                {"post_id": post_id, "watch_percent": percent, "watch_duration": 0, "timestamp": 0}
                for post_id, percent in db_watches
            ]
        
        # Create Redis session
        redis_client.create_session(
            session_id=session_id,
            user_id=user_id,
            initial_watches=initial_watches
        )
        
        return {
            "session_id": session_id,
            "is_new": True,
            "user_type": "logged_in" if user_id else "anonymous",
            "watches_count": len(initial_watches)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize session: {str(e)}"
        )


@router.post("/track")
async def track_watch_event(
    request: WatchEventRequest,
    x_session_id: str = Header(..., description="Session ID from /session/init"),
    redis_client: RedisSessionClient = Depends(get_redis_session_client)
):
    """
    Track video watch event.
    
    **Call this when:**
    - Video finishes (event_type: "finish")
    - User pauses (event_type: "pause")
    - User seeks/fast forwards (event_type: "seek")
    - Periodic progress update (event_type: "progress")
    
    **Request:**
    ```json
    {
        "post_id": "uuid",
        "watch_percent": 0.85,
        "watch_duration": 45.5,
        "event_type": "pause"
    }
    ```
    
    **Headers:**
    - X-Session-Id: Session ID from /session/init
    """
    try:
        success = redis_client.track_watch(
            session_id=x_session_id,
            post_id=request.post_id,
            watch_percent=request.watch_percent,
            watch_duration=request.watch_duration,
            event_type=request.event_type
        )
        
        # NOTE: We do NOT invalidate cached recommendations here.
        # - 5-min TTL handles natural cache expiration
        # - Background worker pre-computes fresh recs every 30s
        # - Aggressive invalidation causes cache misses → discovery fallback
        
        return {
            "status": "tracked" if success else "failed",
            "session_id": x_session_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track watch: {str(e)}"
        )


@router.get("/feed")
async def get_recommended_feed(
    limit: int = Query(5, ge=1, le=20),  # Default 5 posts
    offset: int = Query(0, ge=0),
    content_type: Optional[ContentType] = None,
    x_session_id: Optional[str] = Header(None, description="Session ID"),
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase),
    redis_client: RedisSessionClient = Depends(get_redis_session_client),
    recommendation_engine: RecommendationEngine = Depends(get_recommendation_engine)
):
    """
    Get recommended feed.
    
    **Returns 5 posts by default.**
    Frontend should prefetch when user starts playing post #4.
    
    Uses Redis session for:
    1. Get cached recommendations if available
    2. Otherwise, compute from session watches
    3. Cache new recommendations in Redis
    
    **Headers:**
    - X-Session-Id: Session ID from /session/init (optional, falls back to discovery)
    """
    try:
        post_ids = []
        recommendation_type = "discovery"
        from_cache = False
        watched_ids = []  # Track watched videos to exclude from discovery
        user_id = current_user.id if current_user else None
        
        if x_session_id:
            # Get watched videos from session
            session_watches = redis_client.get_session_watches(x_session_id)
            watched_ids = [w.get("post_id") for w in session_watches if w.get("post_id")]
            
            # Try to get cached recommendations first
            cached = redis_client.get_cached_recommendations(x_session_id)
            
            if cached and cached.get("post_ids"):
                # Use cached recommendations (skip already shown via offset)
                all_ids = cached["post_ids"]
                # Filter out any watched videos from cached recommendations
                filtered_ids = [pid for pid in all_ids if pid not in watched_ids]
                post_ids = filtered_ids[offset:offset + limit]
                if post_ids:  # Only mark from_cache if we actually have results
                    recommendation_type = cached.get("type", "session")
                    from_cache = True
                    
            # Extend session TTL on activity
            redis_client.extend_session_ttl(x_session_id, user_id)
        
        # Fall back to discovery feed (allow replay if user watched all videos)
        if not post_ids:
            post_ids = await recommendation_engine.get_discovery_feed(
                limit=limit,
                difficulty="beginner",
                exclude_ids=watched_ids,  # Exclude videos user has already watched
                allow_replay=True  # Allow replaying if user watched all videos
            )
            recommendation_type = "discovery"
            from_cache = False
        
        # Fetch post details
        if post_ids:
            query = supabase.table("posts").select(
                "*, subtitles(*)"
            ).in_("id", post_ids).eq("status", PostStatus.READY.value)
            
            if content_type:
                query = query.eq("content_type", content_type.value)
            
            response = query.execute()
            
            # Preserve order from recommendation engine
            post_map = {p["id"]: p for p in response.data}
            ordered_posts = [post_map[pid] for pid in post_ids if pid in post_map]
            
            # Get user's liked and saved posts if logged in (single RPC call)
            user_interactions = {}
            if current_user:
                service_supabase = get_service_supabase()
                try:
                    # Use optimized RPC function for batch check
                    interactions_response = service_supabase.rpc(
                        "get_user_interactions",
                        {"p_user_id": current_user.id, "p_post_ids": post_ids}
                    ).execute()
                    user_interactions = {
                        r["post_id"]: {"is_liked": r["is_liked"], "is_saved": r["is_saved"]}
                        for r in interactions_response.data
                    }
                except Exception:
                    # Fallback to separate queries if RPC not available
                    likes_response = service_supabase.table("post_likes").select(
                        "post_id"
                    ).eq("user_id", current_user.id).in_("post_id", post_ids).execute()
                    saves_response = service_supabase.table("saved_posts").select(
                        "post_id"
                    ).eq("user_id", current_user.id).in_("post_id", post_ids).execute()
                    liked_ids = {l["post_id"] for l in likes_response.data}
                    saved_ids = {s["post_id"] for s in saves_response.data}
                    user_interactions = {
                        pid: {"is_liked": pid in liked_ids, "is_saved": pid in saved_ids}
                        for pid in post_ids
                    }
            
            posts = []
            for post_data in ordered_posts:
                # Transform subtitles data from DB format
                post_data = transform_post_data(post_data)
                interaction = user_interactions.get(post_data["id"], {})
                post_data["is_liked"] = interaction.get("is_liked", False)
                post_data["is_saved"] = interaction.get("is_saved", False)
                posts.append(PostResponse(**post_data))
        else:
            posts = []
        
        return {
            "posts": posts,
            "total": len(posts),
            "offset": offset,
            "limit": limit,
            "has_more": True,  # Always allow fetching more (replay enabled)
            "recommendation_type": recommendation_type,
            "from_cache": from_cache,
            "prefetch_at": 4  # Tell frontend to prefetch when playing post #4
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}"
        )


@router.get("/similar/{post_id}")
async def get_similar_posts(
    post_id: str,
    limit: int = Query(5, ge=1, le=20),
    supabase: Client = Depends(get_supabase),
    redis_client: RedisSessionClient = Depends(get_redis_session_client),
    recommendation_engine: RecommendationEngine = Depends(get_recommendation_engine)
):
    """
    Get posts similar to a specific post.
    
    Uses vector similarity search on embeddings for accurate content matching.
    Results are cached in Redis for 10 minutes.
    
    Returns minimal fields for "You may like" card display.
    """
    try:
        # Try to get cached similar posts first (fast path)
        similar_ids = redis_client.get_cached_similar_posts(post_id, limit)
        
        if not similar_ids:
            # Verify post exists and get similar posts
            post_response = supabase.table("posts").select("id").eq(
                "id", post_id
            ).execute()
            
            if not post_response.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Post not found"
                )
            
            # Get similar posts using AI embeddings
            similar_ids = await recommendation_engine.get_similar_videos(
                video_id=post_id,
                limit=limit
            )
            # Cache the results
            if similar_ids:
                redis_client.cache_similar_posts(post_id, similar_ids, limit)
        
        if not similar_ids:
            return []
        
        # Fetch only fields needed for "You may like" cards
        similar_response = supabase.table("posts").select(
            "id, title, thumbnail_url, duration, difficulty_level, views_count, tags"
        ).in_("id", similar_ids).eq("status", PostStatus.READY.value).execute()
        
        # Preserve similarity order
        post_map = {p["id"]: p for p in similar_response.data}
        ordered_posts = [post_map[pid] for pid in similar_ids if pid in post_map]
        
        return ordered_posts
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get similar posts: {str(e)}"
        )
