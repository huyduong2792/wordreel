-- Migration: Optimize comments for better performance
-- Run this in Supabase SQL Editor

-- ============================================================
-- 1. ADD MISSING INDEXES
-- ============================================================

-- Index for fetching replies (parent_id lookup)
CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON post_comments(parent_id);

-- Composite index for fetching top-level comments sorted by date
CREATE INDEX IF NOT EXISTS idx_comments_post_parent_created 
    ON post_comments(post_id, parent_id, created_at DESC);

-- Index for comment_likes lookups
CREATE INDEX IF NOT EXISTS idx_comment_likes_comment_id ON comment_likes(comment_id);
CREATE INDEX IF NOT EXISTS idx_comment_likes_user_id ON comment_likes(user_id);

-- Composite index for the most common query: "has user X liked comment Y?"
CREATE INDEX IF NOT EXISTS idx_comment_likes_user_comment 
    ON comment_likes(user_id, comment_id);

-- ============================================================
-- 2. ADD TRIGGER FOR comment_likes COUNT (auto-update likes_count)
-- ============================================================

CREATE OR REPLACE FUNCTION update_comment_likes_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE post_comments 
        SET likes_count = likes_count + 1 
        WHERE id = NEW.comment_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE post_comments 
        SET likes_count = GREATEST(0, likes_count - 1) 
        WHERE id = OLD.comment_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_comment_likes_count ON comment_likes;
CREATE TRIGGER trigger_comment_likes_count
    AFTER INSERT OR DELETE ON comment_likes
    FOR EACH ROW EXECUTE FUNCTION update_comment_likes_count();

-- ============================================================
-- 3. ADD TRIGGER FOR replies_count (auto-update on reply create/delete)
-- ============================================================

CREATE OR REPLACE FUNCTION update_comment_replies_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.parent_id IS NOT NULL THEN
        UPDATE post_comments 
        SET replies_count = replies_count + 1 
        WHERE id = NEW.parent_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' AND OLD.parent_id IS NOT NULL THEN
        UPDATE post_comments 
        SET replies_count = GREATEST(0, replies_count - 1) 
        WHERE id = OLD.parent_id;
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_comment_replies_count ON post_comments;
CREATE TRIGGER trigger_comment_replies_count
    AFTER INSERT OR DELETE ON post_comments
    FOR EACH ROW EXECUTE FUNCTION update_comment_replies_count();

-- ============================================================
-- 4. RLS POLICIES FOR comment_likes (if not exists)
-- ============================================================

ALTER TABLE comment_likes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Anyone can view comment likes" ON comment_likes;
CREATE POLICY "Anyone can view comment likes" ON comment_likes 
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Users can like comments" ON comment_likes;
CREATE POLICY "Users can like comments" ON comment_likes 
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can unlike comments" ON comment_likes;
CREATE POLICY "Users can unlike comments" ON comment_likes 
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- 5. VERIFY INDEXES (run this to check)
-- ============================================================

-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'post_comments';
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'comment_likes';
