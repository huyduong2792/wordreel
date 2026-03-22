"""
Comment API endpoints
Supports both legacy video_id and new post_id
"""
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from supabase import Client
from models.schemas import CommentCreate, CommentResponse
from database.supabase_client import get_supabase, get_service_supabase
from auth.utils import get_current_user, get_current_user_optional
from api.dependencies import (
    RateLimiter,
    InputSanitizer,
    get_comment_rate_limiter,
    get_sanitizer
)
from database.utils import ensure_user_exists

router = APIRouter()


@router.get("/post/{post_id}", response_model=List[CommentResponse])
async def get_post_comments(
    post_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase)
):
    """Get comments for a post (any content type)"""
    try:
        response = supabase.table("post_comments").select(
            "*, users(username, avatar_url)"
        ).eq("post_id", post_id).is_(
            "parent_id", "null"
        ).order("created_at", desc=True).range(
            offset, offset + limit - 1
        ).execute()
        
        # Batch fetch liked status to avoid N+1 queries
        comment_ids = [c["id"] for c in response.data]
        liked_comment_ids = set()
        
        if current_user and comment_ids:
            likes_response = supabase.table("comment_likes").select(
                "comment_id"
            ).eq("user_id", current_user.id).in_(
                "comment_id", comment_ids
            ).execute()
            liked_comment_ids = {like["comment_id"] for like in likes_response.data}
        
        comments = []
        for comment_data in response.data:
            user_data = comment_data.pop("users")
            comment_data["user_name"] = user_data["username"]
            comment_data["user_avatar"] = user_data.get("avatar_url")
            comment_data["is_liked"] = comment_data["id"] in liked_comment_ids
            comments.append(CommentResponse(**comment_data))
        
        return comments
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comments: {str(e)}"
        )


@router.get("/{comment_id}/replies", response_model=List[CommentResponse])
async def get_comment_replies(
    comment_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_user_optional),
    supabase: Client = Depends(get_supabase)
):
    """Get replies for a specific comment"""
    try:
        response = supabase.table("post_comments").select(
            "*, users(username, avatar_url)"
        ).eq("parent_id", comment_id).order(
            "created_at", desc=False  # Show oldest replies first
        ).range(offset, offset + limit - 1).execute()
        
        # Batch fetch liked status to avoid N+1 queries
        reply_ids = [r["id"] for r in response.data]
        liked_reply_ids = set()
        
        if current_user and reply_ids:
            likes_response = supabase.table("comment_likes").select(
                "comment_id"
            ).eq("user_id", current_user.id).in_(
                "comment_id", reply_ids
            ).execute()
            liked_reply_ids = {like["comment_id"] for like in likes_response.data}
        
        replies = []
        for comment_data in response.data:
            user_data = comment_data.pop("users")
            comment_data["user_name"] = user_data["username"]
            comment_data["user_avatar"] = user_data.get("avatar_url")
            comment_data["is_liked"] = comment_data["id"] in liked_reply_ids
            replies.append(CommentResponse(**comment_data))
        
        return replies
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get replies: {str(e)}"
        )


# Legacy endpoint for backward compatibility
@router.get("/{video_id}", response_model=List[CommentResponse])
async def get_comments(
    video_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_user_optional)
):
    """Get comments for a video (legacy - use /post/{post_id} instead)"""
    return await get_post_comments(video_id, limit, offset, current_user)


@router.post("/", response_model=CommentResponse)
async def create_comment(
    comment: CommentCreate,
    current_user = Depends(get_current_user),
    rate_limiter: RateLimiter = Depends(get_comment_rate_limiter),
    sanitizer: InputSanitizer = Depends(get_sanitizer),
    supabase: Client = Depends(get_service_supabase)
):
    """Create a new comment or reply"""
    # Rate limiting - raises 429 if exceeded
    rate_limiter.check(current_user.id)
    
    # Sanitize content - raises 400 if empty after sanitization
    sanitized_content = sanitizer.sanitize_text(comment.content)
    
    try:
        # Ensure user exists in users table
        ensure_user_exists(supabase, current_user)
        
        # If replying, verify parent exists and is a top-level comment (no nested replies)
        if comment.parent_id:
            parent_check = supabase.table("post_comments").select(
                "id, parent_id"
            ).eq("id", comment.parent_id).execute()
            
            if not parent_check.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent comment not found"
                )
            
            # Prevent nested replies (reply to reply)
            if parent_check.data[0].get("parent_id"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot reply to a reply. Only top-level comments can have replies."
                )
        
        comment_data = {
            "post_id": comment.post_id,
            "user_id": current_user.id,
            "content": sanitized_content,
            "parent_id": comment.parent_id
        }
        
        response = supabase.table("post_comments").insert(
            comment_data
        ).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create comment"
            )
        
        created_comment = response.data[0]
        
        # NOTE: replies_count is auto-updated by database trigger (003_optimize_comments.sql)
        # Do NOT manually increment here to avoid double counting
        
        user_response = supabase.table("users").select(
            "username, avatar_url"
        ).eq("id", current_user.id).execute()
        
        user_data = user_response.data[0]
        created_comment["user_name"] = user_data["username"]
        created_comment["user_avatar"] = user_data.get("avatar_url")
        created_comment["is_liked"] = False
        created_comment["likes_count"] = 0
        created_comment["replies_count"] = 0
        
        return CommentResponse(**created_comment)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create comment: {str(e)}"
        )


@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: str,
    current_user = Depends(get_current_user),
    supabase: Client = Depends(get_service_supabase)
):
    """Delete a comment"""
    try:
        comment_check = supabase.table("post_comments").select("user_id").eq(
            "id", comment_id
        ).execute()
        
        if not comment_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        if comment_check.data[0]["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this comment"
            )
        
        supabase.table("post_comments").delete().eq(
            "id", comment_id
        ).execute()
        
        return {"message": "Comment deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete comment: {str(e)}"
        )


@router.post("/{comment_id}/like")
async def like_comment(
    comment_id: str,
    current_user = Depends(get_current_user),
    rate_limiter: RateLimiter = Depends(get_comment_rate_limiter),
    supabase: Client = Depends(get_service_supabase)
):
    """Like or unlike a comment"""
    # Rate limiting
    rate_limiter.check(current_user.id)
    
    try:
        # Ensure user exists in users table
        ensure_user_exists(supabase, current_user)
        
        like_check = supabase.table("comment_likes").select("id").eq(
            "comment_id", comment_id
        ).eq("user_id", current_user.id).execute()
        
        # Get current comment to check likes_count
        comment = supabase.table("post_comments").select("likes_count").eq(
            "id", comment_id
        ).execute()
        
        if not comment.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found"
            )
        
        current_likes = comment.data[0]["likes_count"] or 0
        
        if like_check.data:
            # Unlike: delete like and decrement count
            supabase.table("comment_likes").delete().eq(
                "id", like_check.data[0]["id"]
            ).execute()
            # Decrement likes_count (ensure minimum 0)
            new_count = max(0, current_likes - 1)
            supabase.table("post_comments").update({
                "likes_count": new_count
            }).eq("id", comment_id).execute()
            return {"liked": False, "likes_count": new_count}
        else:
            # Like: insert like and increment count
            supabase.table("comment_likes").insert({
                "comment_id": comment_id,
                "user_id": current_user.id
            }).execute()
            # Increment likes_count
            new_count = current_likes + 1
            supabase.table("post_comments").update({
                "likes_count": new_count
            }).eq("id", comment_id).execute()
            return {"liked": True, "likes_count": new_count}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to like comment: {str(e)}"
        )
