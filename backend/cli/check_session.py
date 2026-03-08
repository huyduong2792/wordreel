#!/usr/bin/env python3
"""
CLI tool to check session watch history and recommendations.

Usage:
    python -m cli.check_session <session_id>
    python -m cli.check_session 89b54236-312f-48d5-a97d-87d3a217c73c

Run inside the API container:
    docker compose exec api python -m cli.check_session <session_id>
"""
import sys
import json
import argparse
from datetime import datetime

from services.redis_client import get_redis_session_client
from database.supabase_client import get_service_supabase


def format_timestamp(ts: float) -> str:
    """Format Unix timestamp to readable string"""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID"""
    import re
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(value))


def get_post_titles(post_ids: list) -> dict:
    """Fetch post titles from database"""
    if not post_ids:
        return {}
    
    # Filter out invalid UUIDs (e.g., mock-1, test-123)
    valid_ids = [pid for pid in post_ids if is_valid_uuid(pid)]
    invalid_ids = [pid for pid in post_ids if not is_valid_uuid(pid)]
    
    titles = {}
    
    # Add placeholder titles for invalid IDs
    for pid in invalid_ids:
        titles[pid] = f"[INVALID ID: {pid}]"
    
    if not valid_ids:
        return titles
    
    supabase = get_service_supabase()
    result = supabase.table("posts").select("id, title").in_("id", valid_ids).execute()
    for p in result.data:
        titles[p["id"]] = p["title"]
    
    return titles


def get_user_likes(user_id: str) -> list:
    """Fetch liked video IDs from database"""
    if not user_id:
        return []
    
    supabase = get_service_supabase()
    result = supabase.table("post_likes").select("post_id").eq("user_id", user_id).execute()
    return [r["post_id"] for r in result.data]


def get_db_watch_history(user_id: str, limit: int = 50) -> list:
    """Fetch watch history from database"""
    if not user_id:
        return []
    
    supabase = get_service_supabase()
    result = (
        supabase.table("view_history")
        .select("post_id, watch_percent, updated_at")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


def check_session(session_id: str, verbose: bool = False):
    """Check session watch history and recommendations"""
    redis_client = get_redis_session_client()
    
    print("=" * 70)
    print(f"SESSION: {session_id}")
    print("=" * 70)
    
    # Check user info
    user_info = redis_client.get_session_user(session_id)
    if not user_info:
        print("\n❌ Session not found in Redis")
        return
    
    print(f"\nUser Type: {'Logged In' if user_info.get('logged_in') else 'Anonymous'}")
    user_id = user_info.get("user_id")
    if user_id:
        print(f"User ID: {user_id}")
    
    # Get watches from Redis
    watches = redis_client.get_session_watches(session_id)
    
    if not watches:
        print("\n📺 REDIS WATCHES: None")
    else:
        watched_ids = [w["post_id"] for w in watches]
        titles = get_post_titles(watched_ids)
        
        print(f"\n📺 REDIS WATCHES ({len(watches)}):")
        print("-" * 70)
        
        for w in watches:
            post_id = w["post_id"]
            title = titles.get(post_id, "Unknown")[:50]
            percent = w.get("watch_percent", 0) * 100
            event = w.get("event_type", "unknown")
            
            # Status icon based on watch percent
            if percent >= 90:
                icon = "✅"
            elif percent >= 50:
                icon = "🔵"
            else:
                icon = "⚪"
            
            print(f"  {icon} [{percent:5.1f}%] {title}...")
            
            if verbose:
                duration = w.get("watch_duration", 0)
                timestamp = w.get("timestamp", 0)
                print(f"      ID: {post_id}")
                print(f"      Duration: {duration:.1f}s | Event: {event} | Time: {format_timestamp(timestamp)}")
    
    # Get DB watch history (only for logged-in users)
    if user_id:
        db_watches = get_db_watch_history(user_id, limit=20)
        
        if not db_watches:
            print("\n📚 DB WATCH HISTORY: None")
        else:
            db_post_ids = [w["post_id"] for w in db_watches]
            titles = get_post_titles(db_post_ids)
            
            print(f"\n📚 DB WATCH HISTORY ({len(db_watches)}):")
            print("-" * 70)
            
            for w in db_watches:
                post_id = w["post_id"]
                title = titles.get(post_id, "Unknown")[:50]
                percent = (w.get("watch_percent") or 0) * 100
                updated_at = w.get("updated_at", "")[:19]
                
                # Status icon based on watch percent
                if percent >= 90:
                    icon = "✅"
                elif percent >= 50:
                    icon = "🔵"
                else:
                    icon = "⚪"
                
                print(f"  {icon} [{percent:5.1f}%] {title}...")
                
                if verbose:
                    print(f"      ID: {post_id}")
                    print(f"      Updated: {updated_at}")
        
        # Get liked videos (only for logged-in users)
        liked_ids = get_user_likes(user_id)
        
        if not liked_ids:
            print("\n❤️  LIKED VIDEOS: None")
        else:
            titles = get_post_titles(liked_ids)
            
            print(f"\n❤️  LIKED VIDEOS ({len(liked_ids)}):")
            print("-" * 70)
            
            for post_id in liked_ids[:10]:  # Show first 10
                title = titles.get(post_id, "Unknown")[:55]
                print(f"  ❤️  {title}...")
                
                if verbose:
                    print(f"      ID: {post_id}")
            
            if len(liked_ids) > 10:
                print(f"  ... and {len(liked_ids) - 10} more")
    else:
        print("\n📚 DB WATCH HISTORY: N/A (anonymous user)")
        print("\n❤️  LIKED VIDEOS: N/A (anonymous user)")
    
    # Get recommendations
    cached_recs = redis_client.get_cached_recommendations(session_id)
    
    if not cached_recs:
        print("\n🎯 RECOMMENDATIONS: Not cached (will be computed on next worker cycle)")
    else:
        rec_ids = cached_recs.get("post_ids", [])
        rec_type = cached_recs.get("type", "unknown")
        cached_at = cached_recs.get("cached_at", 0)
        
        titles = get_post_titles(rec_ids)
        
        print(f"\n🎯 RECOMMENDATIONS ({len(rec_ids)} videos, type: {rec_type}):")
        print(f"   Cached at: {format_timestamp(cached_at)}")
        print("-" * 70)
        
        for i, post_id in enumerate(rec_ids[:10], 1):  # Show first 10
            title = titles.get(post_id, "Unknown")[:55]
            print(f"  {i:2}. {title}...")
            
            if verbose:
                print(f"      ID: {post_id}")
        
        if len(rec_ids) > 10:
            print(f"  ... and {len(rec_ids) - 10} more")
    
    print("\n" + "=" * 70)


def list_sessions():
    """List all active sessions"""
    redis_client = get_redis_session_client()
    sessions = redis_client.get_all_sessions_for_recommendations(limit=50)
    
    print("=" * 70)
    print("ACTIVE SESSIONS")
    print("=" * 70)
    
    if not sessions:
        print("\nNo active sessions found.")
        return
    
    print(f"\nFound {len(sessions)} sessions:\n")
    
    for session_id in sessions:
        user_info = redis_client.get_session_user(session_id)
        watches = redis_client.get_session_watches(session_id)
        cached_recs = redis_client.get_cached_recommendations(session_id)
        
        user_type = "👤" if user_info and user_info.get("logged_in") else "👻"
        watch_count = len(watches) if watches else 0
        has_recs = "✓" if cached_recs else "✗"
        
        print(f"  {user_type} {session_id}")
        print(f"     Watches: {watch_count} | Recs cached: {has_recs}")
    
    print("\n" + "=" * 70)


def flush_session(session_id: str, flush_all: bool = False):
    """
    Flush session data.
    
    By default (soft flush): Only clears watches and recommendations, keeps session alive.
    With --flush-all (hard flush): Deletes entire session including user info.
    """
    redis_client = get_redis_session_client()
    
    flush_type = "HARD" if flush_all else "SOFT"
    print("=" * 70)
    print(f"FLUSHING SESSION ({flush_type}): {session_id}")
    print("=" * 70)
    
    # Check if session exists
    user_info = redis_client.get_session_user(session_id)
    if not user_info:
        print("\n❌ Session not found in Redis")
        return
    
    # Get counts before deletion
    watches = redis_client.get_session_watches(session_id)
    cached_recs = redis_client.get_cached_recommendations(session_id)
    
    print(f"\nClearing:")
    print(f"  - Watches: {len(watches) if watches else 0}")
    print(f"  - Cached recommendations: {'Yes' if cached_recs else 'No'}")
    if flush_all:
        print(f"  - User info: Yes (session will be destroyed)")
    else:
        print(f"  - User info: No (session kept alive)")
    
    try:
        client = redis_client.client
        
        # Always clear watches and recommendations
        client.delete(f"session:{session_id}:watches")
        client.delete(f"session:{session_id}:recommendations")
        
        # Only delete user info on hard flush
        if flush_all:
            client.delete(f"session:{session_id}:user")
        
        # Remove from pending syncs
        client.srem("pending_syncs", session_id)
        
        if flush_all:
            print(f"\n✅ Session destroyed completely")
        else:
            print(f"\n✅ Watches and recommendations cleared (session still active)")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n" + "=" * 70)


def refresh_recommendations(session_id: str):
    """Force refresh recommendations for a session"""
    import asyncio
    
    redis_client = get_redis_session_client()
    
    print("=" * 70)
    print(f"REFRESHING RECOMMENDATIONS: {session_id}")
    print("=" * 70)
    
    # Check if session exists
    user_info = redis_client.get_session_user(session_id)
    if not user_info:
        print("\n❌ Session not found in Redis")
        return
    
    watches = redis_client.get_session_watches(session_id)
    user_id = user_info.get("user_id") if user_info.get("logged_in") else None
    
    # For logged-in users, we can generate recommendations from likes even without watches
    if not watches and not user_id:
        print("\n❌ No watches found and not logged in - cannot generate recommendations")
        return
    
    print(f"\nSession has {len(watches) if watches else 0} watched videos")
    if user_id:
        print(f"  User is logged in (will also use liked videos from DB)")
    
    # Clear existing recommendations
    redis_client.invalidate_recommendations(session_id)
    print("  → Cleared cached recommendations")
    
    # Import and run recommendation computation
    try:
        from services.container import get_recommendation_engine
        
        recommendation_engine = get_recommendation_engine()
        
        # Convert watches to tuples
        session_watches = [
            (w["post_id"], w.get("watch_percent", 0.5))
            for w in watches
        ] if watches else []
        
        async def compute():
            # Enhance with DB history for logged-in users
            all_watches = session_watches.copy()
            if user_id:
                db_watches = await recommendation_engine.load_user_watch_history(
                    user_id=user_id,
                    limit=50
                )
                session_post_ids = {w[0] for w in session_watches}
                for post_id, percent in db_watches:
                    if post_id not in session_post_ids:
                        all_watches.append((post_id, percent * 0.8))
            
            # Compute recommendations (pass user_id to get liked videos from DB)
            post_ids = await recommendation_engine.get_watch_based_recommendations(
                session_watches=all_watches,
                user_id=user_id,
                limit=30
            )
            return post_ids
        
        print("  → Computing recommendations...")
        post_ids = asyncio.run(compute())
        
        if post_ids:
            # Cache recommendations
            redis_client.cache_recommendations(
                session_id=session_id,
                post_ids=post_ids,
                recommendation_type="session"
            )
            print(f"  → Cached {len(post_ids)} recommendations")
            
            # Show first 5 recommendations
            titles = get_post_titles(post_ids[:5])
            print(f"\n🎯 TOP 5 RECOMMENDATIONS:")
            print("-" * 70)
            for i, post_id in enumerate(post_ids[:5], 1):
                title = titles.get(post_id, "Unknown")[:55]
                print(f"  {i}. {title}...")
        else:
            print("  → No recommendations generated (using discovery fallback)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Check session watch history and recommendations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m cli.check_session 89b54236-312f-48d5-a97d-87d3a217c73c
  python -m cli.check_session 89b54236-312f-48d5-a97d-87d3a217c73c -v
  python -m cli.check_session --list
  python -m cli.check_session 89b54236-312f-48d5-a97d-87d3a217c73c --refresh
  python -m cli.check_session 89b54236-312f-48d5-a97d-87d3a217c73c --flush       # soft flush (keeps session)
  python -m cli.check_session 89b54236-312f-48d5-a97d-87d3a217c73c --flush-all   # hard flush (destroys session)
        """
    )
    
    parser.add_argument(
        "session_id",
        nargs="?",
        help="Session ID to check"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output including post IDs and timestamps"
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List all active sessions"
    )
    parser.add_argument(
        "-r", "--refresh",
        action="store_true",
        help="Force refresh recommendations for the session"
    )
    parser.add_argument(
        "-f", "--flush",
        action="store_true",
        help="Soft flush: Clear watches and recommendations, keep session alive"
    )
    parser.add_argument(
        "--flush-all",
        action="store_true",
        help="Hard flush: Destroy entire session (watches, recommendations, user info)"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_sessions()
    elif args.session_id:
        if args.flush_all:
            flush_session(args.session_id, flush_all=True)
        elif args.flush:
            flush_session(args.session_id, flush_all=False)
        elif args.refresh:
            refresh_recommendations(args.session_id)
        else:
            check_session(args.session_id, verbose=args.verbose)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
