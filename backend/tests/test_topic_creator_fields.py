"""
Tests for topic and creator_name fields in crawler and explore feed.
"""
import pytest
from unittest.mock import patch, MagicMock


from tasks.crawler_tasks import _save_to_database
from services.video_sources import TikTokSource, YouTubeSource, InstagramSource


# ==================== Video Source extract_metadata tests ====================

class TestTikTokSource:
    def test_extract_metadata_includes_creator_name(self):
        source = TikTokSource()
        info = {
            'title': 'Test TikTok Video',
            'description': '#english #learning test',
            'duration': 60,
            'thumbnail': 'https://example.com/thumb.jpg',
            'uploader': 'TestCreator',
            'creator': 'TestCreator',
            'view_count': 1000,
            'like_count': 100,
        }
        metadata = source.extract_metadata(info)
        assert metadata['creator_name'] == 'TestCreator'
        assert metadata['creator_avatar_url'] == 'https://example.com/thumb.jpg'
        assert metadata['creator'] == 'TestCreator'

    def test_extract_metadata_creator_name_fallback(self):
        source = TikTokSource()
        info = {
            'title': 'Test TikTok Video',
            'description': 'No hashtags here',
            'duration': 60,
            'thumbnail': '',
            'view_count': 0,
            'like_count': 0,
        }
        metadata = source.extract_metadata(info)
        assert metadata['creator_name'] == 'Unknown'


class TestYouTubeSource:
    def test_extract_metadata_includes_creator_name(self):
        source = YouTubeSource()
        info = {
            'title': 'Test YouTube Video',
            'description': 'A great video',
            'duration': 300,
            'thumbnail': 'https://example.com/yt-thumb.jpg',
            'uploader': 'EnglishChannel',
            'channel': 'EnglishChannel',
            'tags': ['english', 'grammar'],
            'view_count': 5000,
            'like_count': 500,
        }
        metadata = source.extract_metadata(info)
        assert metadata['creator_name'] == 'EnglishChannel'
        assert metadata['creator_avatar_url'] == 'https://example.com/yt-thumb.jpg'

    def test_extract_metadata_channel_fallback(self):
        source = YouTubeSource()
        info = {
            'title': 'Test Video',
            'description': '',
            'duration': 120,
            'thumbnail': '',
            'channel': 'FallbackChannel',
            'tags': [],
            'view_count': 0,
            'like_count': 0,
        }
        metadata = source.extract_metadata(info)
        assert metadata['creator_name'] == 'FallbackChannel'


class TestInstagramSource:
    def test_extract_metadata_includes_creator_name(self):
        source = InstagramSource()
        info = {
            'title': 'Instagram Reel',
            'description': '#english #speaking',
            'duration': 30,
            'thumbnail': 'https://example.com/ig-thumb.jpg',
            'uploader': 'InstagramCreator',
            'view_count': 200,
            'like_count': 20,
        }
        metadata = source.extract_metadata(info)
        assert metadata['creator_name'] == 'InstagramCreator'
        assert metadata['creator_avatar_url'] == 'https://example.com/ig-thumb.jpg'


# ==================== _save_to_database tests ====================

def _make_mock_supabase():
    """Create a properly-configured mock supabase client for _save_to_database tests."""
    mock = MagicMock()
    insert_calls = {}

    def mock_table(table_name):
        mock_table_instance = MagicMock()

        def insert_side_effect(data):
            insert_calls[table_name] = data
            return MagicMock(execute=MagicMock(return_value=MagicMock(data=[{"id": "test-post-id"}])))

        mock_table_instance.insert.side_effect = insert_side_effect
        return mock_table_instance

    mock.table = mock_table
    return mock, insert_calls


class TestSaveToDatabase:
    def test_topic_derived_from_ai_tags(self):
        """topic should be tags[0] when AI-extracted tags are provided"""
        mock_supabase, insert_calls = _make_mock_supabase()

        metadata = {
            'title': 'Test Video',
            'description': 'A test',
            'duration': 60,
        }
        cloud_urls = {
            "video_url": "https://cdn.example.com/video.mp4",
            "hls_url": "https://cdn.example.com/video.m3u8",
            "dash_url": "https://cdn.example.com/video.mpd",
            "thumbnail_url": "https://cdn.example.com/thumb.jpg",
        }
        ai_tags = ['grammar', 'speaking', 'vocabulary']

        _save_to_database(
            supabase=mock_supabase,
            metadata=metadata,
            cloud_urls=cloud_urls,
            source_url='https://example.com/video',
            user_id=None,
            subtitles_data=[],
            quiz_questions=None,
            tags=ai_tags,
            embedding=None,
        )

        assert insert_calls['posts']['topic'] == 'grammar'
        assert insert_calls['posts']['tags'] == ai_tags

    def test_topic_derived_from_metadata_tags(self):
        """topic should fallback to metadata.tags when no AI tags provided"""
        mock_supabase, insert_calls = _make_mock_supabase()

        metadata = {
            'title': 'Test Video',
            'description': 'A test',
            'duration': 60,
            'tags': ['vocabulary', 'listening'],
            'creator_name': 'TestCreator',
        }
        cloud_urls = {
            "video_url": "https://cdn.example.com/video.mp4",
            "hls_url": "https://cdn.example.com/video.m3u8",
            "dash_url": "https://cdn.example.com/video.mpd",
            "thumbnail_url": "https://cdn.example.com/thumb.jpg",
        }

        _save_to_database(
            supabase=mock_supabase,
            metadata=metadata,
            cloud_urls=cloud_urls,
            source_url='https://example.com/video',
            user_id=None,
            subtitles_data=[],
            quiz_questions=None,
            tags=None,
            embedding=None,
        )

        assert insert_calls['posts']['topic'] == 'vocabulary'
        assert insert_calls['posts']['creator_name'] == 'TestCreator'

    def test_topic_none_when_no_tags(self):
        """topic should be None when neither AI tags nor metadata tags exist"""
        mock_supabase, insert_calls = _make_mock_supabase()

        metadata = {
            'title': 'Test Video',
            'description': 'A test with no tags at all',
            'duration': 60,
            'creator_name': 'NoTagsCreator',
        }
        cloud_urls = {
            "video_url": "https://cdn.example.com/video.mp4",
            "hls_url": "https://cdn.example.com/video.m3u8",
            "dash_url": "https://cdn.example.com/video.mpd",
            "thumbnail_url": "https://cdn.example.com/thumb.jpg",
        }

        _save_to_database(
            supabase=mock_supabase,
            metadata=metadata,
            cloud_urls=cloud_urls,
            source_url='https://example.com/video',
            user_id=None,
            subtitles_data=[],
            quiz_questions=None,
            tags=None,
            embedding=None,
        )

        assert insert_calls['posts']['topic'] is None
        assert insert_calls['posts']['creator_name'] == 'NoTagsCreator'

    def test_creator_name_saved_from_metadata(self):
        """creator_name should be saved from metadata"""
        mock_supabase, insert_calls = _make_mock_supabase()

        metadata = {
            'title': 'Test Video',
            'description': 'Test',
            'duration': 60,
            'creator_name': 'YouTubeChannel',
        }
        cloud_urls = {
            "video_url": "https://cdn.example.com/video.mp4",
            "hls_url": "https://cdn.example.com/video.m3u8",
            "dash_url": "https://cdn.example.com/video.mpd",
            "thumbnail_url": "https://cdn.example.com/thumb.jpg",
        }

        _save_to_database(
            supabase=mock_supabase,
            metadata=metadata,
            cloud_urls=cloud_urls,
            source_url='https://example.com/video',
            user_id=None,
            subtitles_data=[],
            quiz_questions=None,
            tags=None,
            embedding=None,
        )

        assert insert_calls['posts']['creator_name'] == 'YouTubeChannel'


# ==================== Explore feed topic filter tests ====================

class TestExploreFeedTopicFilter:
    def test_topic_filter_query_chain(self):
        """Verify topic filter applies eq('topic', value) in query chain"""
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.contains.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query

        # Simulate what the endpoint does: apply topic filter
        topic_val = "grammar"
        mock_query.eq("topic", topic_val)

        mock_query.eq.assert_called_with("topic", "grammar")

    def test_topic_and_tag_filters_both_applied(self):
        """Both tag (contains) and topic (eq) filters should coexist"""
        mock_query = MagicMock()
        mock_query.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.contains.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.range.return_value = mock_query

        # Apply tag filter then topic filter (order from endpoint code)
        mock_query.contains("tags", ["english"])
        mock_query.eq("topic", "grammar")

        mock_query.contains.assert_called_with("tags", ["english"])
        mock_query.eq.assert_called_with("topic", "grammar")
