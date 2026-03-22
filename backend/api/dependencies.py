"""
FastAPI Dependency Injection Module

Provides reusable dependencies for API routes following DI pattern.
All dependencies should be used with FastAPI's Depends() mechanism.

Usage:
    from api.dependencies import RateLimiter, get_rate_limiter
    
    @router.post("/")
    async def create_item(
        rate_limiter: RateLimiter = Depends(get_rate_limiter("item", 10, 60)),
        current_user = Depends(get_current_user)
    ):
        rate_limiter.check(current_user.id)  # Raises 429 if exceeded
        ...
"""
import re
import html
from typing import Callable
from fastapi import HTTPException, status
from services.redis_client import get_redis_session_client, RedisSessionClient


class RateLimiter:
    """
    Rate limiter dependency for protecting endpoints from abuse.
    
    Uses Redis sliding window counter for distributed rate limiting.
    
    Example:
        # In route handler
        rate_limiter: RateLimiter = Depends(get_rate_limiter("comments", 10, 60))
        rate_limiter.check(user_id)  # Raises HTTPException 429 if exceeded
    """
    
    def __init__(
        self,
        redis_client: RedisSessionClient,
        resource: str,
        max_requests: int,
        window_seconds: int
    ):
        self.redis_client = redis_client
        self.resource = resource
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def check(self, identifier: str) -> None:
        """
        Check rate limit for identifier. Raises HTTPException if exceeded.
        
        Args:
            identifier: Unique identifier (e.g., user_id, ip_address)
            
        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        key = f"{self.resource}:{identifier}"
        is_allowed, remaining = self.redis_client.check_rate_limit(
            key, self.max_requests, self.window_seconds
        )
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Please wait before trying again.",
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(self.window_seconds)
                }
            )


def get_rate_limiter(
    resource: str,
    max_requests: int = 10,
    window_seconds: int = 60
) -> Callable[[], RateLimiter]:
    """
    Factory function to create rate limiter dependency.
    
    Args:
        resource: Resource name for rate limit key (e.g., "comments", "likes")
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        
    Returns:
        Dependency function for FastAPI Depends()
        
    Usage:
        @router.post("/")
        async def create_comment(
            rate_limiter: RateLimiter = Depends(get_rate_limiter("comments", 10, 60)),
            current_user = Depends(get_current_user)
        ):
            rate_limiter.check(current_user.id)
            ...
    """
    def dependency() -> RateLimiter:
        redis_client = get_redis_session_client()
        return RateLimiter(
            redis_client=redis_client,
            resource=resource,
            max_requests=max_requests,
            window_seconds=window_seconds
        )
    return dependency


class InputSanitizer:
    """
    Input sanitization dependency for user-provided content.
    
    Provides methods to sanitize different types of user input
    to prevent XSS, injection attacks, and clean malformed input.
    """
    
    @staticmethod
    def sanitize_text(content: str, max_length: int = 2000) -> str:
        """
        Sanitize text content (comments, descriptions, etc.)
        
        - HTML escapes special characters
        - Removes control characters
        - Normalizes whitespace
        - Truncates to max_length
        
        Args:
            content: Raw user input
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
            
        Raises:
            HTTPException: 400 if result is empty
        """
        # HTML escape to prevent XSS
        content = html.escape(content)
        # Remove null bytes and control characters
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', content)
        # Normalize whitespace (collapse multiple spaces/newlines)
        content = re.sub(r'\s+', ' ', content).strip()
        # Truncate
        content = content[:max_length]
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content cannot be empty after sanitization"
            )
        
        return content


def get_sanitizer() -> InputSanitizer:
    """Get InputSanitizer instance for dependency injection."""
    return InputSanitizer()


# Pre-configured rate limiters for common use cases
get_comment_rate_limiter = get_rate_limiter("comments", max_requests=10, window_seconds=60)
