# WordReel Backend Setup Guide

## Quick Start

✅ **All Supabase credentials are already configured in `.env.example`!**

Just run:
```bash
cp .env.example .env
```

---

## 1. Run the Database Schema

Create the database tables:

1. Go to https://kmtcisddqekkrzurxvih.supabase.co
2. Click on **SQL Editor** in the sidebar
3. Click **New query**
4. Copy the contents of `backend/database/schema.sql`
5. Paste it into the SQL Editor
6. Click **Run** (or press Ctrl+Enter)
7. Verify all tables were created successfully

---

## 2. Optional: OpenAI API Key

If you want AI-generated quizzes:

1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Add it to your `.env` as `OPENAI_API_KEY`

---

## 3. Start the Backend

```bash
# Copy environment file
cp .env.example .env

# Install dependencies
pip install -r requirements.txt

# Start Redis
redis-server

# Start Celery worker (in another terminal)
celery -A celery_app worker --loglevel=info -Q subtitle_processing,crawler

# Start API server
python main.py
```

Visit: http://localhost:8000/docs for API documentation

---

## Storage Architecture

📦 **Videos & Thumbnails**: Stored on your cloud provider (huydq.staging.mediacdn.vn) via TUS upload

💾 **Database**: Supabase PostgreSQL (user data, video metadata, subtitles, quizzes)

🔄 **Upload Flow**:
1. Client uploads video via TUS to cloud provider
2. Backend registers video URL and generates subtitles
3. Subtitles stored in Supabase database
4. Cloud provider handles HLS/DASH/thumbnail generation

---

## Checklist

- [x] Supabase credentials configured in `.env.example`
- [x] TUS server credentials configured
- [ ] Ran `schema.sql` in Supabase SQL Editor
- [ ] (Optional) Got OpenAI API key for quiz generation
