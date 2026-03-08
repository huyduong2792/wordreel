"""
TUS protocol client for resumable file uploads using tuspy library
"""
import os
import subprocess
import json
from typing import Optional, Dict, BinaryIO
from tusclient import client as tus_client
from config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


def verify_video_file(file_path: str) -> Dict:
    """
    Verify that the video file has both video and audio streams.
    Returns dict with file info.
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        probe = json.loads(result.stdout)
        
        streams = probe.get('streams', [])
        video_stream = next((s for s in streams if s['codec_type'] == 'video'), None)
        audio_stream = next((s for s in streams if s['codec_type'] == 'audio'), None)
        
        info = {
            'has_video': video_stream is not None,
            'has_audio': audio_stream is not None,
            'duration': float(probe.get('format', {}).get('duration', 0)),
            'size': int(probe.get('format', {}).get('size', 0)),
            'format': probe.get('format', {}).get('format_name', 'unknown'),
        }
        
        if video_stream:
            info['video_codec'] = video_stream.get('codec_name', 'unknown')
            info['width'] = video_stream.get('width', 0)
            info['height'] = video_stream.get('height', 0)
        
        if audio_stream:
            info['audio_codec'] = audio_stream.get('codec_name', 'unknown')
        
        logger.info("Video file verified", **info)
        return info
        
    except Exception as e:
        logger.error("Failed to verify video file", error=str(e))
        return {'has_video': False, 'has_audio': False, 'error': str(e)}


class TUSClient:
    """Client for TUS resumable upload protocol using tuspy"""
    
    def __init__(
        self,
        server_url: Optional[str] = None,
        credential_id: Optional[str] = None,
        credential_secret: Optional[str] = None
    ):
        """Initialize TUS client"""
        self.server_url = server_url or settings.TUS_SERVER_URL
        self.credential_id = credential_id or settings.TUS_CREDENTIAL_ID
        self.credential_secret = credential_secret or settings.TUS_CREDENTIAL_SECRET
        self.auth_type = settings.TUS_AUTH_TYPE
        
        # Validate configuration
        if not self.server_url:
            raise ValueError("TUS_SERVER_URL is required")
        if not self.credential_id or not self.credential_secret:
            raise ValueError("TUS credentials are required")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for TUS requests"""
        return {
            "X-Auth-Type": self.auth_type,
            "X-App-Credential-Id": self.credential_id,
            "X-App-Credential-Secret": self.credential_secret,
        }
    
    @staticmethod
    def _encode_metadata(value: str) -> str:
        """Encode metadata value for TUS (base64)"""
        import base64
        return base64.b64encode(value.encode()).decode()
    
    def upload_file_sync(
        self,
        file_path: str,
        metadata: Optional[Dict[str, str]] = None,
        chunk_size: int = 5 * 1024 * 1024,  # 5MB chunks
        verify_video: bool = True
    ) -> Dict[str, str]:
        """
        Upload a file using TUS protocol (synchronous for Celery tasks)
        
        Args:
            file_path: Path to the file to upload
            metadata: Additional metadata for the upload
            chunk_size: Size of each chunk (default 5MB)
            verify_video: If True, verify video has both audio and video streams
        
        Returns:
            Dict with upload_url and file_path
        """
        try:
            # Verify video file if requested
            if verify_video:
                file_info = verify_video_file(file_path)
                if not file_info.get('has_video'):
                    logger.warning("Video file has no video stream!", file_path=file_path, info=file_info)
                if not file_info.get('has_audio'):
                    logger.warning("Video file has no audio stream!", file_path=file_path, info=file_info)
            
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            logger.info("Starting TUS upload", filename=filename, file_size=file_size)
            
            # Prepare metadata
            meta = metadata or {}
            meta["filename"] = filename
            
            # Create TUS client with custom headers
            my_client = tus_client.TusClient(
                self.server_url,
                headers=self._get_headers()
            )
            
            # Create uploader with file
            uploader = my_client.uploader(
                file_path=file_path,
                chunk_size=chunk_size,
                metadata=meta,
                retries=3,
                retry_delay=5
            )
            
            # Upload the file
            uploader.upload()
            
            # Get the upload URL
            upload_url = uploader.url
            remote_file_path = meta.get("file_path", "")
            
            logger.info(
                "TUS upload completed",
                filename=filename,
                file_size=file_size,
                upload_url=upload_url,
                file_path=remote_file_path
            )
            
            return {
                "upload_url": upload_url,
                "file_path": remote_file_path
            }
            
        except Exception as e:
            logger.error("Failed to upload file via TUS", file_path=file_path, error=str(e))
            raise Exception(f"Failed to upload file: {str(e)}")
    
    def upload_file_object_sync(
        self,
        file_obj: BinaryIO,
        filename: str,
        file_size: int,
        metadata: Optional[Dict[str, str]] = None,
        chunk_size: int = 5 * 1024 * 1024
    ) -> Dict[str, str]:
        """
        Upload a file object using TUS protocol (synchronous for Celery tasks)
        
        Args:
            file_obj: File-like object to upload
            filename: Name of the file
            file_size: Size of the file in bytes
            metadata: Additional metadata for the upload
            chunk_size: Size of each chunk (default 5MB)
        
        Returns:
            Dict with upload_url and file_path
        """
        try:
            logger.info("Starting TUS upload from file object", filename=filename, file_size=file_size)
            
            # Prepare metadata
            meta = metadata or {}
            meta["filename"] = filename
            
            # Create TUS client with custom headers
            my_client = tus_client.TusClient(
                self.server_url,
                headers=self._get_headers()
            )
            
            # Create uploader with file stream
            uploader = my_client.uploader(
                file_stream=file_obj,
                chunk_size=chunk_size,
                metadata=meta,
                retries=3,
                retry_delay=5
            )
            
            # Upload the file
            uploader.upload()
            
            # Get the upload URL
            upload_url = uploader.url
            remote_file_path = meta.get("file_path", "")
            
            logger.info(
                "TUS upload completed",
                filename=filename,
                file_size=file_size,
                upload_url=upload_url,
                file_path=remote_file_path
            )
            
            return {
                "upload_url": upload_url,
                "file_path": remote_file_path
            }
            
        except Exception as e:
            logger.error("Failed to upload file object via TUS", filename=filename, error=str(e))
            raise Exception(f"Failed to upload file: {str(e)}")
    
    # Async versions for FastAPI routes
    async def upload_file(
        self,
        file_path: str,
        metadata: Optional[Dict[str, str]] = None,
        chunk_size: int = 5 * 1024 * 1024,
        verify_video: bool = True
    ) -> Dict[str, str]:
        """Async wrapper for upload_file_sync"""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.upload_file_sync(file_path, metadata, chunk_size, verify_video)
        )
    
    async def upload_file_object(
        self,
        file_obj: BinaryIO,
        filename: str,
        file_size: int,
        metadata: Optional[Dict[str, str]] = None,
        chunk_size: int = 5 * 1024 * 1024
    ) -> Dict[str, str]:
        """Async wrapper for upload_file_object_sync"""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.upload_file_object_sync(file_obj, filename, file_size, metadata, chunk_size)
        )
    
    @staticmethod
    def get_cloud_urls(file_path: str, base_url: str = "http://huydq.staging.mediacdn.vn") -> Dict[str, str]:
        """
        Generate cloud CDN URLs from file path
        
        Args:
            file_path: File path (e.g., /2026/02/01/video.mp4)
            base_url: Base CDN URL
        
        Returns:
            Dict with video_url, hls_url, dash_url, thumbnail_url
        """
        if not file_path.startswith("/"):
            file_path = "/" + file_path
        
        video_url = f"{base_url}{file_path}"
        
        # Extract filename for thumbnail
        filename = os.path.basename(file_path)
        dir_path = os.path.dirname(file_path)
        
        return {
            "video_url": video_url,
            "hls_url": f"{video_url}/master.m3u8",
            "dash_url": f"{video_url}/manifest.mpd",
            "thumbnail_url": f"{base_url}{dir_path}/.{filename}.jpg"
        }


# Singleton instance
_tus_client: Optional[TUSClient] = None


def get_tus_client() -> TUSClient:
    """Get TUS client singleton"""
    global _tus_client
    if _tus_client is None:
        _tus_client = TUSClient()
    return _tus_client
