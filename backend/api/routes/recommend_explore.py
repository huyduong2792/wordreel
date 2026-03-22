"""
Explore API endpoints - curated explore feed based on popularity
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from supabase import Client
from models.schemas import PostResponse, PostStatus, ContentType
from database.supabase_client import get_supabase, get_service_supabase
from database.utils import transform_post_data
from auth.utils import get_current_user_optional

router = APIRouter(tags=["Explore"])


@router.get("")
async def get_explore_feed(
    limit: int = Query(20, ge=1, le=30),
    offset: int = Query(0, ge=0),
    tag: Optional[str] = Query(None, description="Filter by tag/category"),
    content_type: Optional[ContentType] = Query(None),
    supabase: Client = Depends(get_supabase),
    current_user=Depends(get_current_user_optional)
):
    """
    Get curated explore feed based on popularity.

    Returns posts sorted by likes_count desc then views_count desc.
    Optionally filtered by tag or content type.

    **Query params:**
    - limit: Number of posts to return (1-30, default 20)
    - offset: Pagination offset (default 0)
    - tag: Filter by tag/category
    - content_type: Filter by content type (video, image_slides, audio, quiz)

    **Returns:**
    ```json
    {
        "posts": [...],
        "total": 100,
        "offset": 0,
        "limit": 20,
        "has_more": true
    }
    ```
    """
    try:
        # Build query
        query = supabase.table("posts").select(
            "*, subtitles(*)"
        ).eq("status", PostStatus.READY.value)

        # Apply tag filter
        if tag:
            query = query.contains("tags", [tag])

        # Apply content type filter
        if content_type:
            query = query.eq("content_type", content_type.value)

        # Order by likes_count desc, then views_count desc
        query = query.order("likes_count", desc=True).order("views_count", desc=True)

        # Apply pagination
        query = query.range(offset, offset + limit - 1)

        response = query.execute()

        # Batch fetch user interactions if logged in
        post_ids = [p["id"] for p in response.data]
        user_interactions = {}

        if current_user and post_ids:
            service_supabase = get_service_supabase()
            try:
                # Try optimized RPC function first
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

        # Batch fetch user info for post authors
        user_ids = list({p["user_id"] for p in response.data if p.get("user_id")})
        user_info_map = {}
        if user_ids:
            users_response = supabase.table("users").select("id, username, avatar_url").in_("id", user_ids).execute()
            user_info_map = {u["id"]: u for u in users_response.data}

        # Transform posts and build response
        posts = []
        for post_data in response.data:
            post_data = transform_post_data(post_data)
            interaction = user_interactions.get(post_data["id"], {})
            post_data["is_liked"] = interaction.get("is_liked", False)
            post_data["is_saved"] = interaction.get("is_saved", False)
            user_info = user_info_map.get(post_data.get("user_id", ""))
            post_data["username"] = user_info.get("username") if user_info else None
            post_data["user_avatar_url"] = user_info.get("avatar_url") if user_info else None
            posts.append(PostResponse(**post_data))

        has_more = len(response.data) == limit

        return {
            "posts": posts,
            "total": len(response.data),
            "offset": offset,
            "limit": limit,
            "has_more": has_more
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get explore feed: {str(e)}"
        )
