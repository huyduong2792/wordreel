"""
Posts API endpoints - unified content management
Supports: video, image_slides, audio, quiz content types
"""
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from models.schemas import PostResponse
from database.supabase_client import get_supabase, get_service_supabase
from database.utils import transform_post_data, ensure_user_exists
from auth.utils import get_current_user, get_current_user_optional

router = APIRouter()


@router.post("/batch")
async def get_posts_batch(
    post_ids: List[str],
    current_user = Depends(get_current_user_optional)
):
    """Get multiple posts by IDs in a single request"""
    if not post_ids:
        return []
    
    if len(post_ids) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 posts per batch request"
        )
    
    supabase = get_supabase()
    
    try:
        response = supabase.table("posts").select(
            "*, subtitles(*)"
        ).in_("id", post_ids).execute()
        
        if not response.data:
            return []
        
        # Create a map for quick lookup
        posts_map = {}
        for post_data in response.data:
            post_data = transform_post_data(post_data)
            post_data["is_liked"] = False
            post_data["is_saved"] = False
            posts_map[post_data["id"]] = post_data
        
        # Batch check user interactions
        if current_user and posts_map:
            like_check = supabase.table("post_likes").select("post_id").eq(
                "user_id", current_user.id
            ).in_("post_id", list(posts_map.keys())).execute()
            
            for like in like_check.data:
                if like["post_id"] in posts_map:
                    posts_map[like["post_id"]]["is_liked"] = True
            
            save_check = supabase.table("saved_posts").select("post_id").eq(
                "user_id", current_user.id
            ).in_("post_id", list(posts_map.keys())).execute()
            
            for save in save_check.data:
                if save["post_id"] in posts_map:
                    posts_map[save["post_id"]]["is_saved"] = True
        
        # Return posts in the requested order
        result = []
        for post_id in post_ids:
            if post_id in posts_map:
                result.append(PostResponse(**posts_map[post_id]))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get posts batch: {str(e)}"
        )


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    current_user = Depends(get_current_user_optional)
):
    """Get post by ID"""
    supabase = get_supabase()
    
    try:
        response = supabase.table("posts").select(
            "*, subtitles(*)"
        ).eq("id", post_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        post_data = response.data[0]
        
        # Transform subtitles data
        post_data = transform_post_data(post_data)
        
        # Check interactions
        is_liked = False
        is_saved = False
        
        if current_user:
            like_check = supabase.table("post_likes").select("id").eq(
                "post_id", post_id
            ).eq("user_id", current_user.id).execute()
            is_liked = len(like_check.data) > 0
            
            save_check = supabase.table("saved_posts").select("id").eq(
                "post_id", post_id
            ).eq("user_id", current_user.id).execute()
            is_saved = len(save_check.data) > 0
        
        post_data["is_liked"] = is_liked
        post_data["is_saved"] = is_saved
        
        # Increment view count
        supabase.rpc("increment_post_views", {"p_post_id": post_id}).execute()
        
        return PostResponse(**post_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get post: {str(e)}"
        )


@router.post("/{post_id}/like")
async def like_post(
    post_id: str,
    current_user = Depends(get_current_user)
):
    """Like or unlike a post"""
    supabase = get_service_supabase()  # Use service client to bypass RLS
    
    try:
        # Ensure user exists in users table
        ensure_user_exists(supabase, current_user)
        
        like_check = supabase.table("post_likes").select("id").eq(
            "post_id", post_id
        ).eq("user_id", current_user.id).execute()
        
        if like_check.data:
            supabase.table("post_likes").delete().eq(
                "id", like_check.data[0]["id"]
            ).execute()
            return JSONResponse(content={"liked": False})
        else:
            supabase.table("post_likes").insert({
                "post_id": post_id,
                "user_id": current_user.id
            }).execute()
            return JSONResponse(content={"liked": True})
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to like post: {str(e)}"
        )


@router.post("/{post_id}/save")
async def save_post(
    post_id: str,
    current_user = Depends(get_current_user)
):
    """Save or unsave a post"""
    supabase = get_service_supabase()  # Use service client to bypass RLS
    
    try:
        # Ensure user exists in users table
        ensure_user_exists(supabase, current_user)
        
        save_check = supabase.table("saved_posts").select("id").eq(
            "post_id", post_id
        ).eq("user_id", current_user.id).execute()
        
        if save_check.data:
            supabase.table("saved_posts").delete().eq(
                "id", save_check.data[0]["id"]
            ).execute()
            return JSONResponse(content={"saved": False})
        else:
            supabase.table("saved_posts").insert({
                "post_id": post_id,
                "user_id": current_user.id
            }).execute()
            return JSONResponse(content={"saved": True})
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save post: {str(e)}"
        )
