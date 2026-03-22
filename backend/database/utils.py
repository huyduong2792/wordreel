"""
Shared database utility functions used across route modules.
Per database.md convention, transform_post_data lives here.
"""
from typing import Dict, Any


def transform_post_data(post_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform post data from database format to schema format.
    Extracts subtitles from the subtitles table JSONB column.
    """
    # Extract subtitles from the subtitles table join
    subtitles_rows = post_data.get("subtitles", [])

    # The subtitles table has: id, post_id, language, subtitles (JSONB array)
    # We need to extract the JSONB subtitles array
    all_subtitles = []

    for row in subtitles_rows:
        if isinstance(row, dict) and "subtitles" in row:
            # The 'subtitles' column contains the JSONB array
            subtitles_data = row.get("subtitles", [])
            if isinstance(subtitles_data, list):
                all_subtitles.extend(subtitles_data)

    post_data["subtitles"] = all_subtitles
    return post_data


def ensure_user_exists(supabase, user) -> None:
    """Ensure user exists in users table (upsert from auth user)"""
    user_metadata = user.user_metadata or {}
    supabase.table("users").upsert({
        "id": user.id,
        "email": user.email,
        "username": user_metadata.get("name") or user_metadata.get("full_name") or user.email.split("@")[0],
        "avatar_url": user_metadata.get("avatar_url") or user_metadata.get("picture"),
    }, on_conflict="id").execute()
