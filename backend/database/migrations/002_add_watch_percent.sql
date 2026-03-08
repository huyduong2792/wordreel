-- Migration: Add watch_percent and updated_at to view_history
-- For unified session-based recommendations

-- Add watch_percent column (0.0 to 1.0)
ALTER TABLE view_history 
ADD COLUMN IF NOT EXISTS watch_percent REAL DEFAULT 0.0;

-- Add updated_at column for tracking last update
ALTER TABLE view_history 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Create index on updated_at for efficient sorting
CREATE INDEX IF NOT EXISTS idx_view_history_updated_at 
ON view_history(user_id, updated_at DESC);

-- Create unique constraint to allow upsert behavior
-- (One record per user-post combination)
ALTER TABLE view_history 
DROP CONSTRAINT IF EXISTS view_history_user_post_unique;

ALTER TABLE view_history 
ADD CONSTRAINT view_history_user_post_unique UNIQUE (user_id, post_id);

-- Update RLS policy to allow updates
DROP POLICY IF EXISTS "Users can update own history" ON view_history;
CREATE POLICY "Users can update own history" ON view_history FOR UPDATE 
    USING (auth.uid() = user_id);

-- Comment explaining the schema
COMMENT ON COLUMN view_history.watch_percent IS 'Percentage of video watched (0.0 to 1.0). Used for recommendation weighting.';
COMMENT ON COLUMN view_history.updated_at IS 'Last time this view record was updated.';
