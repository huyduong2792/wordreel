"""
Embedding service for generating vector embeddings using OpenAI
"""
from typing import List, Optional
from openai import AsyncOpenAI
from config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


class EmbeddingService:
    """Generate and manage vector embeddings for content-based recommendations"""
    
    # OpenAI embedding model - small, fast, cheap
    MODEL = "text-embedding-3-small"
    DIMENSIONS = 1536
    
    def __init__(self):
        self._client: Optional[AsyncOpenAI] = None
    
    @property
    def client(self) -> AsyncOpenAI:
        """Lazy-load OpenAI client"""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a piece of text.
        
        Args:
            text: Text to embed (max ~8000 tokens)
            
        Returns:
            List of floats representing the embedding vector (1536 dimensions)
        """
        try:
            # Truncate if too long (roughly 4 chars per token)
            max_chars = 30000
            if len(text) > max_chars:
                text = text[:max_chars]
            
            response = await self.client.embeddings.create(
                model=self.MODEL,
                input=text,
                encoding_format="float"
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error("Failed to generate embedding", error=str(e))
            raise
    
    async def generate_video_embedding(
        self,
        title: str,
        transcript: str,
        tags: Optional[List[str]] = None
    ) -> List[float]:
        """
        Generate embedding for a video based on its content.
        Combines title, transcript, and tags for richer representation.
        """
        # Build combined text for embedding
        parts = [f"Title: {title}"]
        
        if tags:
            parts.append(f"Topics: {', '.join(tags)}")
        
        if transcript:
            # Use first 2000 chars of transcript (most important content)
            parts.append(f"Content: {transcript[:2000]}")
        
        combined_text = "\n".join(parts)
        
        return await self.generate_embedding(combined_text)
    
    async def generate_user_interest_embedding(
        self,
        liked_video_embeddings: List[List[float]],
        saved_video_embeddings: List[List[float]],
        watched_video_embeddings: List[List[float]],
        watch_ratios: Optional[List[float]] = None
    ) -> List[float]:
        """
        Generate user interest vector by combining their engaged video embeddings.
        
        Weights:
        - Liked videos: 1.0
        - Saved videos: 1.2 (stronger signal)
        - Watched videos: weighted by watch ratio (0.0 to 1.0)
        """
        if not any([liked_video_embeddings, saved_video_embeddings, watched_video_embeddings]):
            return []
        
        weighted_sum = [0.0] * self.DIMENSIONS
        total_weight = 0.0
        
        # Add liked videos (weight 1.0)
        for emb in liked_video_embeddings:
            for i, v in enumerate(emb):
                weighted_sum[i] += v * 1.0
            total_weight += 1.0
        
        # Add saved videos (weight 1.2)
        for emb in saved_video_embeddings:
            for i, v in enumerate(emb):
                weighted_sum[i] += v * 1.2
            total_weight += 1.2
        
        # Add watched videos (weight by watch ratio)
        for idx, emb in enumerate(watched_video_embeddings):
            ratio = watch_ratios[idx] if watch_ratios and idx < len(watch_ratios) else 0.5
            weight = ratio * 0.8  # Max 0.8 for just watching
            for i, v in enumerate(emb):
                weighted_sum[i] += v * weight
            total_weight += weight
        
        # Normalize
        if total_weight > 0:
            return [v / total_weight for v in weighted_sum]
        
        return weighted_sum
    
    async def generate_weighted_embedding(
        self,
        embeddings: List[List[float]],
        weights: List[float]
    ) -> List[float]:
        """
        Generate weighted average of embeddings.
        
        Args:
            embeddings: List of embedding vectors
            weights: Corresponding weights for each embedding
            
        Returns:
            Weighted average embedding vector
        """
        if not embeddings or not weights:
            return []
        
        if len(embeddings) != len(weights):
            logger.warning("Embeddings and weights length mismatch")
            weights = weights[:len(embeddings)]
        
        weighted_sum = [0.0] * self.DIMENSIONS
        total_weight = sum(weights)
        
        if total_weight == 0:
            return []
        
        for emb, weight in zip(embeddings, weights):
            if weight > 0 and emb:
                for i, v in enumerate(emb):
                    weighted_sum[i] += v * weight
        
        # Normalize
        return [v / total_weight for v in weighted_sum]
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2:
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
