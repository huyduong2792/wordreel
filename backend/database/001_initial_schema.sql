-- Supabase Database Schema for WordReel
-- Multi-content type support: video, image_slides, audio, quiz
-- With pgvector for AI-powered recommendations

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";  -- pgvector for embeddings

-- ============================================================
-- ENUM TYPES
-- ============================================================

-- Content type enum
CREATE TYPE content_type AS ENUM ('video', 'image_slides', 'audio', 'quiz');

-- Post status enum
CREATE TYPE post_status AS ENUM ('pending', 'processing', 'transcribing', 'ready', 'failed');

-- Difficulty level enum  
CREATE TYPE difficulty_level AS ENUM ('beginner', 'intermediate', 'advanced');

-- ============================================================
-- CORE TABLES
-- ============================================================

-- Users table (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    avatar_url TEXT,
    bio TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Posts table (unified content: video, image_slides, audio, quiz)
CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Common fields
    title TEXT NOT NULL,
    description TEXT,
    content_type content_type NOT NULL DEFAULT 'video',
    status post_status NOT NULL DEFAULT 'pending',
    tags TEXT[] DEFAULT '{}',
    difficulty_level difficulty_level DEFAULT 'beginner',
    source_url TEXT UNIQUE,
    thumbnail_url TEXT,
    duration REAL DEFAULT 0,  -- For video/audio: seconds; For slides: 0
    
    -- Video-specific fields (nullable for other content types)
    video_url TEXT,
    hls_url TEXT,
    dash_url TEXT,
    
    -- Audio-specific fields
    audio_url TEXT,
    
    -- Image slides fields (array of image objects)
    -- Format: [{"url": "...", "caption": "...", "order": 1}, ...]
    slides JSONB,
    
    -- Engagement metrics
    views_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    
    -- Vector embedding for AI recommendations (1536 dimensions for OpenAI text-embedding-3-small)
    embedding vector(1536),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_video_content CHECK (
        content_type != 'video' OR video_url IS NOT NULL
    ),
    CONSTRAINT valid_audio_content CHECK (
        content_type != 'audio' OR audio_url IS NOT NULL
    ),
    CONSTRAINT valid_slides_content CHECK (
        content_type != 'image_slides' OR slides IS NOT NULL
    )
);

-- Subtitles/Transcripts table (for video and audio)
CREATE TABLE IF NOT EXISTS subtitles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    language TEXT DEFAULT 'en',
    subtitles JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Post likes table
CREATE TABLE IF NOT EXISTS post_likes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(post_id, user_id)
);

-- Saved posts table
CREATE TABLE IF NOT EXISTS saved_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(post_id, user_id)
);

-- Comments table
CREATE TABLE IF NOT EXISTS post_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES post_comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    likes_count INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Comment likes table
CREATE TABLE IF NOT EXISTS comment_likes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    comment_id UUID REFERENCES post_comments(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(comment_id, user_id)
);

-- Watch/View history table
CREATE TABLE IF NOT EXISTS view_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    view_duration REAL NOT NULL,  -- Seconds for video/audio, slide count for image_slides
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Quizzes table
CREATE TABLE IF NOT EXISTS quizzes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    questions JSONB NOT NULL,
    total_points INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Quiz results table
CREATE TABLE IF NOT EXISTS quiz_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    quiz_id UUID REFERENCES quizzes(id) ON DELETE CASCADE,
    post_id UUID REFERENCES posts(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    total_points INTEGER NOT NULL,
    percentage REAL NOT NULL,
    passed BOOLEAN NOT NULL,
    answers JSONB NOT NULL,
    details JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

-- Posts indexes
CREATE INDEX IF NOT EXISTS idx_posts_content_type ON posts(content_type);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_tags ON posts USING GIN(tags);

-- Relationship indexes
CREATE INDEX IF NOT EXISTS idx_subtitles_post_id ON subtitles(post_id);
CREATE INDEX IF NOT EXISTS idx_post_likes_post_id ON post_likes(post_id);
CREATE INDEX IF NOT EXISTS idx_post_likes_user_id ON post_likes(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_posts_user_id ON saved_posts(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_post_id ON post_comments(post_id);
CREATE INDEX IF NOT EXISTS idx_comments_user_id ON post_comments(user_id);
CREATE INDEX IF NOT EXISTS idx_view_history_user_id ON view_history(user_id);
CREATE INDEX IF NOT EXISTS idx_view_history_post_id ON view_history(post_id);
CREATE INDEX IF NOT EXISTS idx_quiz_results_user_id ON quiz_results(user_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_post_id ON quizzes(post_id);

-- Vector index for fast similarity search (HNSW)
CREATE INDEX IF NOT EXISTS idx_posts_embedding ON posts 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Increment post views
CREATE OR REPLACE FUNCTION increment_post_views(p_post_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE posts
    SET views_count = views_count + 1
    WHERE id = p_post_id;
END;
$$ LANGUAGE plpgsql;

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Update likes count trigger function
CREATE OR REPLACE FUNCTION update_post_likes_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE posts SET likes_count = likes_count + 1 WHERE id = NEW.post_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE posts SET likes_count = likes_count - 1 WHERE id = OLD.post_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Update comments count trigger function
CREATE OR REPLACE FUNCTION update_post_comments_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE posts SET comments_count = comments_count + 1 WHERE id = NEW.post_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE posts SET comments_count = comments_count - 1 WHERE id = OLD.post_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- VECTOR SIMILARITY SEARCH FUNCTIONS
-- ============================================================

-- Match posts by embedding similarity (for recommendations)
CREATE OR REPLACE FUNCTION match_posts_by_embedding(
    query_embedding vector(1536),
    match_count INT DEFAULT 10,
    exclude_ids UUID[] DEFAULT '{}',
    filter_content_type content_type DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    content_type content_type,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.title,
        p.content_type,
        1 - (p.embedding <=> query_embedding) AS similarity
    FROM posts p
    WHERE 
        p.status = 'ready'
        AND p.embedding IS NOT NULL
        AND NOT (p.id = ANY(exclude_ids))
        AND (filter_content_type IS NULL OR p.content_type = filter_content_type)
    ORDER BY p.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================================
-- TRIGGERS
-- ============================================================

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_posts_updated_at ON posts;
CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_comments_updated_at ON post_comments;
CREATE TRIGGER update_comments_updated_at BEFORE UPDATE ON post_comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_post_likes_count ON post_likes;
CREATE TRIGGER trigger_post_likes_count
    AFTER INSERT OR DELETE ON post_likes
    FOR EACH ROW EXECUTE FUNCTION update_post_likes_count();

DROP TRIGGER IF EXISTS trigger_post_comments_count ON post_comments;
CREATE TRIGGER trigger_post_comments_count
    AFTER INSERT OR DELETE ON post_comments
    FOR EACH ROW EXECUTE FUNCTION update_post_comments_count();

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE subtitles ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE post_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE view_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_results ENABLE ROW LEVEL SECURITY;

-- Users policies
DROP POLICY IF EXISTS "Users can view all users" ON users;
CREATE POLICY "Users can view all users" ON users FOR SELECT USING (true);

DROP POLICY IF EXISTS "Users can update own profile" ON users;
CREATE POLICY "Users can update own profile" ON users FOR UPDATE USING (auth.uid() = id);

-- Posts policies
DROP POLICY IF EXISTS "Anyone can view ready posts" ON posts;
CREATE POLICY "Anyone can view ready posts" ON posts FOR SELECT 
    USING (status = 'ready' OR user_id = auth.uid());

DROP POLICY IF EXISTS "Authenticated users can insert posts" ON posts;
CREATE POLICY "Authenticated users can insert posts" ON posts FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own posts" ON posts;
CREATE POLICY "Users can update own posts" ON posts FOR UPDATE 
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own posts" ON posts;
CREATE POLICY "Users can delete own posts" ON posts FOR DELETE 
    USING (auth.uid() = user_id);

-- Subtitles policies
DROP POLICY IF EXISTS "Anyone can view subtitles" ON subtitles;
CREATE POLICY "Anyone can view subtitles" ON subtitles FOR SELECT USING (true);

-- Likes policies
DROP POLICY IF EXISTS "Anyone can view likes" ON post_likes;
CREATE POLICY "Anyone can view likes" ON post_likes FOR SELECT USING (true);

DROP POLICY IF EXISTS "Authenticated users can like" ON post_likes;
CREATE POLICY "Authenticated users can like" ON post_likes FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can unlike own" ON post_likes;
CREATE POLICY "Users can unlike own" ON post_likes FOR DELETE 
    USING (auth.uid() = user_id);

-- Saved posts policies
DROP POLICY IF EXISTS "Users can view own saved" ON saved_posts;
CREATE POLICY "Users can view own saved" ON saved_posts FOR SELECT 
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can save posts" ON saved_posts;
CREATE POLICY "Users can save posts" ON saved_posts FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can unsave posts" ON saved_posts;
CREATE POLICY "Users can unsave posts" ON saved_posts FOR DELETE 
    USING (auth.uid() = user_id);

-- Comments policies
DROP POLICY IF EXISTS "Anyone can view comments" ON post_comments;
CREATE POLICY "Anyone can view comments" ON post_comments FOR SELECT USING (true);

DROP POLICY IF EXISTS "Authenticated users can comment" ON post_comments;
CREATE POLICY "Authenticated users can comment" ON post_comments FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own comments" ON post_comments;
CREATE POLICY "Users can update own comments" ON post_comments FOR UPDATE 
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own comments" ON post_comments;
CREATE POLICY "Users can delete own comments" ON post_comments FOR DELETE 
    USING (auth.uid() = user_id);

-- View history policies
DROP POLICY IF EXISTS "Users can view own history" ON view_history;
CREATE POLICY "Users can view own history" ON view_history FOR SELECT 
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can record view" ON view_history;
CREATE POLICY "Users can record view" ON view_history FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

-- Quiz results policies
DROP POLICY IF EXISTS "Users can view own results" ON quiz_results;
CREATE POLICY "Users can view own results" ON quiz_results FOR SELECT 
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can submit results" ON quiz_results;
CREATE POLICY "Users can submit results" ON quiz_results FOR INSERT 
    WITH CHECK (auth.uid() = user_id);
