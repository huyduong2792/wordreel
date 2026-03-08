# WordReel Backend

Backend API for WordReel - A TikTok-style English learning platform with advanced features like interactive subtitles, quizzes, and personalized recommendations.

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: Supabase (PostgreSQL)
- **Auth**: Supabase Auth (Email/Password, OAuth)
- **Background Jobs**: Celery + Redis (optional - only for crawler)
- **Video Upload**: TUS Protocol (Resumable uploads)
- **Video Processing**: Cloud Provider (HLS/DASH/Thumbnail generation)
- **AI**: OpenAI GPT-4 (Quiz Generation - optional)
- **Video Download**: yt-dlp (optional - only for crawler)
- **CDN**: huydq.staging.mediacdn.vn

## Features

- ✅ User Authentication (Email/Password, Google OAuth)
- ✅ Resumable Video Upload (TUS Protocol - Client & Server)
- ✅ Cloud Video Processing (HLS/DASH/Thumbnails)
- ✅ AI Subtitle Generation (Whisper - stored in your DB)
- ✅ Word-level Subtitle Timing
- ✅ Video Recommendations (Personalized & Trending)
- ✅ Interactive Quizzes (AI-powered with GPT-4)
- ✅ Comments & Likes System
- ✅ Watch History & Analytics
- ✅ Learning Progress Tracking
- ✅ Background Video Crawling (Optional)
- ✅ Native HLS/DASH Support

## Project Structure

```
backend/
├── api/
│   └── routes/
│       ├── auth.py          # Authentication endpoints
│       ├── videos.py        # Video management
│       ├── subtitles.py     # Subtitle endpoints
│       ├── comments.py      # Comments system
│       ├── quizzes.py       # Quiz endpoints
│       ├── analytics.py     # User analytics
│       └── recommendations.py # Video recommendations
├── auth/
│   └── utils.py            # Auth utilities
├── database/
│   ├── supabase_client.py  # Supabase client
│   └── schema.sql          # Database schema
├── models/
│   └── schemas.py          # Pydantic models
├── services/
│   ├── video_processor.py  # Video processing
│   ├── quiz_generator.py   # Quiz generation
│   └── recommendation_engine.py # Recommendations
├── tasks/
│   ├── video_tasks.py      # Video processing tasks
│   └── crawler_tasks.py    # Video crawling tasks
├── main.py                 # FastAPI app
├── config.py               # Configuration
├── celery_app.py           # Celery configuration
└── requirements.txt        # Dependencies
```

## Setup

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install System Dependencies
**Redis** (Optional - only if using video crawler):

```bash
# Redis (for Celery background jobs)
sudo apt-get install redis-server  # Ubuntu/Debian
# or
brew install redis  # macOS
```

**Note**: FFmpeg and Whisper are NOT needed - cloud provider handles video processing!w install redis  # macOS
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Security
SECRET_KEY=your-secret-key-change-in-production
```

### 4. Setup Database

1. Go to your Supabase project
2. Run the SQL from `database/schema.sql` in the SQL Editor
3. Enable Storage buckets:
   - Create bucket: `videos`
   - Create bucket: `thumbnails`
   - Make both public

### 5. Run Services

**Start Redis:**
```bashFastAPI Server (Main Service):**
```bash
python main.py
# or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Optional - If using video crawler:**

Start Redis:
```bash
redis-server
```

Start Celery Worker:
```bash
celery -A celery_app worker --loglevel=info -Q crawler
```

Start Celery Beat (for scheduled crawling):
```bash
celery -A celery_app beat --loglevel=info

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `POST /api/v1/auth/google` - Google OAuth
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/me` - Get current user

### Videos
- `GET /api/v1/videos/feed` - Get video feed
- `GET /api/v1/videos/{video_id}` - Get video details
- `POST /api/v1/videos/upload` - Upload video
- `POST /api/v1/videos/{video_id}/like` - Like/unlike video
- `POST /api/v1/videos/{video_id}/save` - Save/unsave video
- `POST /api/v1/videos/{video_id}/watch` - Record watch history

### Subtitles
- `GET /api/v1/subtitles/{video_id}` - Get video subtitles

### Comments
- `GET /api/v1/comments/{video_id}` - Get video comments
- `POST /api/v1/comments` - Create comment
- `DELETE /api/v1/comments/{comment_id}` - Delete comment

### Quizzes
- `GET /api/v1/quizzes/{video_id}` - Get video quiz
- `POST /api/v1/quizzes/submit` - Submit quiz answers
- `GET /api/v1/quizzes/results/{video_id}` - Get quiz results

### Analytics
- `GET /api/v1/analytics/progress` - Get user progress
- `GET /api/v1/analytics/video/{video_id}` - Get video analytics

### Recommendations
- `POST /api/v1/recommendations` - Get personalized recommendations
- `GET /api/v1/recommendations/similar/{video_id}` - Get similar videos

## Background Tasks

### Video Processing Task
Automatically processes uploaded videos:
1. Extract video metadata
2. Generate subtitles with word timings (Whisper AI)
3. Create thumbnail
4. Generate quiz questions (GPT-4)
5. Update video status to "ready"

### Crawler Tasks
Download videos from external sources:
- TikTok
- YouTube
- Other platforms (via yt-dlp)

Schedule crawling with Celery Beat.

## Development

### Running Tests
```bash
pytest
```

### Code Style
```bash
black .
flake8 .
```

## Production Deployment

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables
Set all required environment variables in your deployment platform.

### Scaling
- Use separate workers for video processing and crawler tasks
- Scale Celery workers based on queue depth
- Use CDN for video delivery (Cloudflare, AWS CloudFront)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License
