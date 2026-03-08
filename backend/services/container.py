"""
Dependency Injection Container
Provides singleton instances of services with proper dependency wiring
"""
from functools import lru_cache
from typing import Optional

from config import get_settings
from services.video_processor import VideoProcessor
from services.quiz_generator import QuizGenerator
from services.embedding_service import EmbeddingService
from services.content_processor import ContentProcessor
from services.recommendation_engine import RecommendationEngine
from services.tus_client import TUSClient


class ServiceContainer:
    """
    IoC Container for dependency injection.
    Provides lazy-loaded singleton instances of all services.
    """
    
    _instance: Optional["ServiceContainer"] = None
    
    def __init__(self):
        self._settings = get_settings()
        self._video_processor: Optional[VideoProcessor] = None
        self._quiz_generator: Optional[QuizGenerator] = None
        self._embedding_service: Optional[EmbeddingService] = None
        self._content_processor: Optional[ContentProcessor] = None
        self._recommendation_engine: Optional[RecommendationEngine] = None
        self._tus_client: Optional[TUSClient] = None
    
    @classmethod
    def get_instance(cls) -> "ServiceContainer":
        """Get singleton container instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset container (useful for testing)"""
        cls._instance = None
    
    @property
    def video_processor(self) -> VideoProcessor:
        """Get VideoProcessor instance"""
        if self._video_processor is None:
            self._video_processor = VideoProcessor()
        return self._video_processor
    
    @property
    def quiz_generator(self) -> QuizGenerator:
        """Get QuizGenerator instance (GPT-4o-mini)"""
        if self._quiz_generator is None:
            self._quiz_generator = QuizGenerator()
        return self._quiz_generator
    
    @property
    def embedding_service(self) -> EmbeddingService:
        """Get EmbeddingService instance (OpenAI text-embedding-3-small)"""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service
    
    @property
    def content_processor(self) -> ContentProcessor:
        """Get ContentProcessor instance with all AI services injected"""
        if self._content_processor is None:
            self._content_processor = ContentProcessor(
                video_processor=self.video_processor,
                quiz_generator=self.quiz_generator,
                embedding_service=self.embedding_service
            )
        return self._content_processor
    
    @property
    def recommendation_engine(self) -> RecommendationEngine:
        """Get RecommendationEngine instance with embedding service injected"""
        if self._recommendation_engine is None:
            self._recommendation_engine = RecommendationEngine(
                embedding_service=self.embedding_service
            )
        return self._recommendation_engine
    
    @property
    def tus_client(self) -> TUSClient:
        """Get TUSClient instance"""
        if self._tus_client is None:
            self._tus_client = TUSClient(
                server_url=self._settings.TUS_SERVER_URL,
                credential_id=self._settings.TUS_CREDENTIAL_ID,
                credential_secret=self._settings.TUS_CREDENTIAL_SECRET
            )
        return self._tus_client


@lru_cache()
def get_container() -> ServiceContainer:
    """Get the service container (cached)"""
    return ServiceContainer.get_instance()


# Convenience functions for direct service access
def get_video_processor() -> VideoProcessor:
    """Get VideoProcessor from container"""
    return get_container().video_processor


def get_quiz_generator() -> QuizGenerator:
    """Get QuizGenerator from container"""
    return get_container().quiz_generator


def get_embedding_service() -> EmbeddingService:
    """Get EmbeddingService from container"""
    return get_container().embedding_service


def get_content_processor() -> ContentProcessor:
    """Get ContentProcessor from container"""
    return get_container().content_processor


def get_recommendation_engine() -> RecommendationEngine:
    """Get RecommendationEngine from container"""
    return get_container().recommendation_engine


def get_tus_client() -> TUSClient:
    """Get TUSClient from container"""
    return get_container().tus_client
