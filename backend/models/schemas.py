"""
Database models and schemas for WordReel
Supports multiple content types: video, image_slides, audio, quiz
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# Enums
class ContentType(str, Enum):
    """Content types supported by the platform"""
    VIDEO = "video"
    IMAGE_SLIDES = "image_slides"
    AUDIO = "audio"
    QUIZ = "quiz"


class TemplateType(str, Enum):
    """Subtitle template types"""
    COLOR_HIGHLIGHT = "color_highlight"
    BOUNCE = "bounce"
    FADE = "fade"
    TYPEWRITER = "typewriter"


class QuestionType(str, Enum):
    """Quiz question types"""
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_BLANK = "fill_blank"
    ARRANGE_SENTENCE = "arrange_sentence"
    TRUE_FALSE = "true_false"


class PostStatus(str, Enum):
    """Post processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    READY = "ready"
    FAILED = "failed"


# Video Models
class WordTiming(BaseModel):
    """Word timing in subtitle"""
    word: str
    start: float
    end: float


class TemplateConfig(BaseModel):
    """Subtitle template configuration"""
    type: TemplateType
    colors: Optional[List[str]] = None
    animation_duration: Optional[float] = 0.3
    
    class Config:
        populate_by_name = True


class Subtitle(BaseModel):
    """Subtitle segment"""
    subtitle_id: str = Field(alias="subtitleId")
    template_config: TemplateConfig = Field(alias="templateConfig")
    text: str
    start_time: float = Field(alias="startTime")
    end_time: float = Field(alias="endTime")
    word_timings: List[WordTiming] = Field(alias="wordTimings")
    
    class Config:
        populate_by_name = True


# Image Slide Models
class ImageSlide(BaseModel):
    """Single slide in an image carousel"""
    url: str
    caption: Optional[str] = None
    order: int = 0
    alt_text: Optional[str] = None


# Post Models (unified content model)
class PostBase(BaseModel):
    """Base post model for all content types"""
    title: str
    description: Optional[str] = None
    content_type: ContentType = ContentType.VIDEO
    duration: float = 0
    thumbnail_url: Optional[str] = None
    tags: List[str] = []
    difficulty_level: Optional[str] = "beginner"
    topic: Optional[str] = None
    creator_name: Optional[str] = None


class PostCreate(PostBase):
    """Post creation model"""
    source_url: Optional[str] = None
    # Video-specific
    video_url: Optional[str] = None
    # Audio-specific
    audio_url: Optional[str] = None
    # Slides-specific
    slides: Optional[List[ImageSlide]] = None


class PostResponse(PostBase):
    """Post response model"""
    id: str
    status: PostStatus
    
    # Video fields
    video_url: Optional[str] = None
    hls_url: Optional[str] = None
    dash_url: Optional[str] = None
    
    # Audio fields
    audio_url: Optional[str] = None
    
    # Image slides
    slides: Optional[List[ImageSlide]] = None
    
    # Subtitles/Transcript
    subtitles: List[Subtitle] = []
    
    # Engagement
    likes_count: int = 0
    comments_count: int = 0
    views_count: int = 0
    shares_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    # User info
    username: Optional[str] = None
    user_avatar_url: Optional[str] = None

    # User interaction flags
    is_liked: bool = False
    is_saved: bool = False

    class Config:
        from_attributes = True


# Subtitle Models
class SubtitleUpload(BaseModel):
    """Upload subtitle file"""
    post_id: str
    language: str = "en"


class SubtitleResponse(BaseModel):
    """Subtitle response"""
    id: str
    post_id: str
    language: str
    subtitles: List[Subtitle]
    created_at: datetime


# Comment Models
class CommentBase(BaseModel):
    """Base comment model"""
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: Optional[str] = None


class CommentCreate(CommentBase):
    """Create comment"""
    post_id: str = Field(..., min_length=1)


class CommentResponse(CommentBase):
    """Comment response"""
    id: str
    post_id: str
    user_id: str
    user_name: str
    user_avatar: Optional[str] = None
    likes_count: int = 0
    replies_count: int = 0
    is_liked: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


# Quiz Models
class QuizOption(BaseModel):
    """Quiz option"""
    id: str
    text: str
    is_correct: bool = False


class QuizQuestion(BaseModel):
    """Quiz question"""
    id: str
    type: QuestionType
    question: str
    options: Optional[List[QuizOption]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    points: int = 10
    difficulty: int = 1  # 1=easiest, 4=hardest (TOEIC-style ordering)


class QuizCreate(BaseModel):
    """Create quiz"""
    post_id: str
    questions: List[QuizQuestion]


class QuizResponse(BaseModel):
    """Quiz response"""
    id: str
    post_id: str
    questions: List[QuizQuestion]
    total_points: int
    created_at: datetime


class QuizSubmission(BaseModel):
    """Submit quiz answers"""
    quiz_id: str
    answers: Dict[str, Any]  # question_id: answer


class QuizResult(BaseModel):
    """Quiz result"""
    quiz_id: str
    score: int
    total_points: int
    percentage: float
    correct_answers: int
    total_questions: int
    passed: bool
    details: List[Dict[str, Any]]


# User Models
class UserBase(BaseModel):
    """Base user model"""
    email: str
    username: str


class UserCreate(UserBase):
    """User creation"""
    password: str


class UserLogin(BaseModel):
    """User login"""
    email: str
    password: str


class UserResponse(UserBase):
    """User response"""
    id: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT Token"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Analytics Models
class ViewHistory(BaseModel):
    """View history entry"""
    post_id: str
    view_duration: float
    completed: bool = False
    quiz_score: Optional[float] = None


# Legacy alias
WatchHistory = ViewHistory


class UserProgress(BaseModel):
    """User learning progress"""
    total_posts_viewed: int
    total_view_time: float  # in seconds
    quizzes_taken: int
    average_quiz_score: float
    posts_completed: int
    current_streak: int  # days
    total_points: int


class PostAnalytics(BaseModel):
    """Post analytics"""
    post_id: str
    views: int
    unique_viewers: int
    average_watch_time: float
    completion_rate: float
    likes: int
    comments: int
    shares: int
    saves: int


# Recommendation/Feed Models
class FeedRequest(BaseModel):
    """Request feed posts"""
    limit: int = 10
    offset: int = 0
    content_type: Optional[ContentType] = None  # Filter by content type
    difficulty_level: Optional[str] = None
    tags: Optional[List[str]] = None


class FeedResponse(BaseModel):
    """Feed response with posts"""
    posts: List[PostResponse]
    total: int
    page: int
    has_more: bool


# Legacy models for backward compatibility
class RecommendationRequest(BaseModel):
    """Request recommendations"""
    limit: int = 10
    offset: int = 0
    difficulty_level: Optional[str] = None
    tags: Optional[List[str]] = None
    content_type: Optional[ContentType] = None


class RecommendationResponse(BaseModel):
    """Recommendation response"""
    posts: List[PostResponse]
    total: int
    page: int
    has_more: bool
