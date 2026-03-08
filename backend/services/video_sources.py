"""
Video source handlers for different platforms
Scalable pattern for adding new video sources
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import yt_dlp
import structlog

logger = structlog.get_logger()


class VideoSource(ABC):
    """Abstract base class for video sources"""
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """Return platform name"""
        pass
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if this source can handle the URL"""
        pass
    
    @abstractmethod
    def get_download_options(self, output_path: str) -> Dict:
        """Get yt-dlp options for this platform"""
        pass
    
    @abstractmethod
    def extract_metadata(self, info: Dict) -> Dict:
        """Extract and normalize metadata from yt-dlp info"""
        pass


class TikTokSource(VideoSource):
    """TikTok video source handler"""
    
    def get_platform_name(self) -> str:
        return "tiktok"
    
    def can_handle(self, url: str) -> bool:
        """Check if URL is from TikTok"""
        tiktok_domains = ['tiktok.com', 'vt.tiktok.com', 'vm.tiktok.com']
        return any(domain in url.lower() for domain in tiktok_domains)
    
    def get_download_options(self, output_path: str) -> Dict:
        """Get TikTok-specific download options"""
        return {
            'format': 'best[height<=1080]',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            # TikTok specific
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
    
    def extract_metadata(self, info: Dict) -> Dict:
        """Extract metadata from TikTok video"""
        # TikTok-specific metadata extraction
        title = info.get('title', 'Untitled TikTok')
        description = info.get('description', '')
        
        # Extract hashtags from description
        tags = []
        if description:
            words = description.split()
            tags = [word[1:] for word in words if word.startswith('#')]
        
        # Add TikTok-specific tags
        if 'tags' in info:
            tags.extend(info['tags'])
        
        # Get creator info
        creator = info.get('uploader', info.get('creator', 'Unknown'))
        
        return {
            'title': title[:200],  # Limit title length
            'description': description[:500] if description else None,
            'duration': info.get('duration', 0),
            'thumbnail': info.get('thumbnail', ''),
            'tags': list(set(tags))[:10],  # Unique tags, max 10
            'creator': creator,
            'view_count': info.get('view_count', 0),
            'like_count': info.get('like_count', 0),
            'platform': 'tiktok'
        }


class YouTubeSource(VideoSource):
    """YouTube video source handler"""
    
    def get_platform_name(self) -> str:
        return "youtube"
    
    def can_handle(self, url: str) -> bool:
        """Check if URL is from YouTube"""
        youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
        return any(domain in url.lower() for domain in youtube_domains)
    
    def get_download_options(self, output_path: str) -> Dict:
        """Get YouTube-specific download options"""
        return {
            'format': 'best[height<=1080][ext=mp4]',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            # YouTube specific
            'nocheckcertificate': True,
        }
    
    def extract_metadata(self, info: Dict) -> Dict:
        """Extract metadata from YouTube video"""
        tags = info.get('tags', []) or []
        if 'categories' in info:
            tags.extend(info['categories'])
        
        return {
            'title': info.get('title', 'Untitled YouTube Video')[:200],
            'description': info.get('description', '')[:500] or None,
            'duration': info.get('duration', 0),
            'thumbnail': info.get('thumbnail', ''),
            'tags': list(set(tags))[:10],
            'creator': info.get('uploader', info.get('channel', 'Unknown')),
            'view_count': info.get('view_count', 0),
            'like_count': info.get('like_count', 0),
            'platform': 'youtube'
        }


class InstagramSource(VideoSource):
    """Instagram/Reels video source handler"""
    
    def get_platform_name(self) -> str:
        return "instagram"
    
    def can_handle(self, url: str) -> bool:
        """Check if URL is from Instagram"""
        return 'instagram.com' in url.lower()
    
    def get_download_options(self, output_path: str) -> Dict:
        """Get Instagram-specific download options"""
        return {
            'format': 'best[height<=1080]',
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }
    
    def extract_metadata(self, info: Dict) -> Dict:
        """Extract metadata from Instagram video"""
        description = info.get('description', '')
        
        # Extract hashtags
        tags = []
        if description:
            words = description.split()
            tags = [word[1:] for word in words if word.startswith('#')]
        
        return {
            'title': info.get('title', 'Instagram Reel')[:200],
            'description': description[:500] or None,
            'duration': info.get('duration', 0),
            'thumbnail': info.get('thumbnail', ''),
            'tags': list(set(tags))[:10],
            'creator': info.get('uploader', 'Unknown'),
            'view_count': info.get('view_count', 0),
            'like_count': info.get('like_count', 0),
            'platform': 'instagram'
        }


class VideoSourceFactory:
    """Factory for creating video source handlers"""
    
    def __init__(self):
        self.sources: List[VideoSource] = [
            TikTokSource(),
            YouTubeSource(),
            InstagramSource(),
        ]
    
    def get_source(self, url: str) -> Optional[VideoSource]:
        """Get the appropriate source handler for a URL"""
        for source in self.sources:
            if source.can_handle(url):
                logger.info("Matched video source", platform=source.get_platform_name(), url=url)
                return source
        
        logger.warning("No matching video source found", url=url)
        return None
    
    def get_supported_platforms(self) -> List[str]:
        """Get list of supported platforms"""
        return [source.get_platform_name() for source in self.sources]
