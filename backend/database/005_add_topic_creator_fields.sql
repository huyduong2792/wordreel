-- Add topic (single-string, derived from AI tags) and creator_name to posts table
ALTER TABLE posts ADD COLUMN IF NOT EXISTS topic TEXT;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS creator_name TEXT;

-- Index for topic filtering in explore feed
CREATE INDEX IF NOT EXISTS idx_posts_topic ON posts(topic);

COMMENT ON COLUMN posts.topic IS 'Single-string main topic, derived from AI-extracted tags. Distinct from tags[].';
COMMENT ON COLUMN posts.creator_name IS 'Creator/channel name from video source (yt-dlp uploader field).';
