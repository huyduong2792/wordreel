"""
Content processing service - handles subtitle, quiz, and embedding generation
Uses dependency injection for video processor, quiz generator, and embedding service
"""
import os
import asyncio
from typing import List, Optional, Protocol
from dataclasses import dataclass, field
from models.schemas import Subtitle, QuizQuestion
import structlog

logger = structlog.get_logger()


class IVideoProcessor(Protocol):
    """Interface for video processing"""
    
    def get_video_info(self, video_path: str) -> dict:
        ...
    
    def extract_audio(self, video_path: str, output_path: Optional[str] = None) -> str:
        ...
    
    def transcribe_audio(self, audio_path: str, language: str = "en") -> List[Subtitle]:
        ...


class IQuizGenerator(Protocol):
    """Interface for quiz generation"""
    
    async def generate_quiz(
        self,
        video_transcript: str,
        video_title: str,
        num_questions: int = 5
    ) -> List[QuizQuestion]:
        ...
    
    async def extract_tags(
        self,
        transcript: str,
        title: str,
        max_tags: int = 5
    ) -> List[str]:
        ...


class IEmbeddingService(Protocol):
    """Interface for embedding generation"""
    
    async def generate_video_embedding(
        self,
        title: str,
        transcript: str,
        tags: Optional[List[str]] = None
    ) -> List[float]:
        ...


@dataclass
class ProcessingResult:
    """Result of content processing"""
    subtitles: List[dict]
    quiz_questions: Optional[List[QuizQuestion]] = None
    duration: float = 0.0
    transcript: str = ""
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None


class ContentProcessor:
    """
    Orchestrates content processing pipeline.
    Uses dependency injection for all AI services.
    """
    
    def __init__(
        self,
        video_processor: IVideoProcessor,
        quiz_generator: IQuizGenerator,
        embedding_service: Optional[IEmbeddingService] = None
    ):
        self._video_processor = video_processor
        self._quiz_generator = quiz_generator
        self._embedding_service = embedding_service
    
    def process_video(
        self,
        video_path: str,
        language: str = "en",
        generate_quiz: bool = True,
        generate_embedding: bool = True,
        video_title: str = "Untitled"
    ) -> ProcessingResult:
        """
        Process video to generate subtitles, quiz, tags, and embedding.
        
        Args:
            video_path: Path to the video file
            language: Language code for transcription
            generate_quiz: Whether to generate quiz questions
            generate_embedding: Whether to generate embedding for recommendations
            video_title: Title for quiz/embedding context
            
        Returns:
            ProcessingResult with subtitles, quiz, tags, embedding, and metadata
        """
        audio_path = None
        
        try:
            # Get video info
            video_info = self._video_processor.get_video_info(video_path)
            duration = video_info.get('duration', 0)
            
            logger.info("Extracting audio", video_path=video_path)
            
            # Extract audio
            audio_path = self._video_processor.extract_audio(video_path)
            
            logger.info("Transcribing audio", language=language)
            
            # Generate subtitles with word timings
            subtitles = self._video_processor.transcribe_audio(audio_path, language=language)
            
            # Convert to dict format for storage
            subtitles_data = self._subtitles_to_dict(subtitles)
            
            logger.info("Subtitles generated", count=len(subtitles_data))
            
            # Build transcript
            transcript = " ".join([s["text"] for s in subtitles_data])
            
            # Run async tasks
            quiz_questions, tags, embedding = asyncio.run(
                self._generate_ai_content(
                    transcript=transcript,
                    video_title=video_title,
                    generate_quiz=generate_quiz and len(transcript) > 50,
                    generate_embedding=generate_embedding and self._embedding_service is not None
                )
            )
            
            return ProcessingResult(
                subtitles=subtitles_data,
                quiz_questions=quiz_questions,
                duration=duration,
                transcript=transcript,
                tags=tags,
                embedding=embedding
            )
            
        finally:
            # Cleanup audio file
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
    
    async def _generate_ai_content(
        self,
        transcript: str,
        video_title: str,
        generate_quiz: bool,
        generate_embedding: bool
    ):
        """Generate quiz, tags, and embedding concurrently"""
        quiz_questions = None
        tags = []
        embedding = None
        
        tasks = []
        task_names = []
        
        # Quiz generation task
        if generate_quiz:
            tasks.append(self._quiz_generator.generate_quiz(transcript, video_title))
            task_names.append("quiz")
        
        # Tag extraction task (always run for recommendations)
        tasks.append(self._quiz_generator.extract_tags(transcript, video_title))
        task_names.append("tags")
        
        # Run quiz and tags first
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for name, result in zip(task_names, results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to generate {name}", error=str(result))
                    continue
                
                if name == "quiz":
                    quiz_questions = result
                    logger.info("Quiz generated", questions=len(quiz_questions) if quiz_questions else 0)
                elif name == "tags":
                    tags = result or []
                    logger.info("Tags extracted", tags=tags)
        
        # Embedding generation (after tags are available)
        if generate_embedding and self._embedding_service:
            try:
                embedding = await self._embedding_service.generate_video_embedding(
                    title=video_title,
                    transcript=transcript,
                    tags=tags
                )
                logger.info("Embedding generated", dimensions=len(embedding) if embedding else 0)
            except Exception as e:
                logger.warning("Failed to generate embedding", error=str(e))
        
        return quiz_questions, tags, embedding
    
    def _subtitles_to_dict(self, subtitles: List[Subtitle]) -> List[dict]:
        """Convert Subtitle models to dict format for storage"""
        return [
            {
                "subtitleId": sub.subtitle_id,
                "templateConfig": {
                    "type": sub.template_config.type.value
                },
                "text": sub.text,
                "startTime": sub.start_time,
                "endTime": sub.end_time,
                "wordTimings": [
                    {
                        "word": wt.word,
                        "start": wt.start,
                        "end": wt.end
                    }
                    for wt in sub.word_timings
                ]
            }
            for sub in subtitles
        ]
