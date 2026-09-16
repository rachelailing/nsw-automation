-- ============================================================
-- AI Dispensing Defect Detective — Database Schema
-- Run this in Supabase SQL Editor to create the required tables.
-- ============================================================

-- ---------------------------------------------------------
-- Sessions: Active conversation state per user
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id      UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    step            TEXT NOT NULL DEFAULT 'questioning',
        -- Possible values: questioning, identifying, ranking, reporting, done
    problem_description TEXT DEFAULT '',
    conversation_history JSONB DEFAULT '[]'::jsonb,
        -- Full message history: [{role, content, timestamp}, ...]
    qa_pairs        JSONB DEFAULT '[]'::jsonb,
        -- Structured Q&A: [{question, answer}, ...]
    defect_type     TEXT,
        -- Identified defect (NULL until Step 2 completes)
    causes          JSONB,
        -- Ranked causes (NULL until Step 3-4 completes)
    image_url       TEXT,
        -- URL of uploaded image in Supabase Storage (NULL if no image)
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ---------------------------------------------------------
-- Case History: Completed cases for RAG / learning database
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_history (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id      UUID REFERENCES sessions(session_id) ON DELETE SET NULL,
    problem_description TEXT NOT NULL,
    defect_type     TEXT NOT NULL,
    causes          JSONB NOT NULL DEFAULT '[]'::jsonb,
        -- [{rank, cause, category, confidence, reasoning}, ...]
    action_plan     TEXT,
    outcome         TEXT,
        -- Optional: technician can record what ultimately fixed the issue
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Index for RAG lookups: find similar cases by defect type
CREATE INDEX IF NOT EXISTS idx_case_history_defect_type
    ON case_history(defect_type);

-- Index for ordering by recency
CREATE INDEX IF NOT EXISTS idx_case_history_created_at
    ON case_history(created_at DESC);


-- ---------------------------------------------------------
-- Uploaded Images: Metadata for dispensing defect images
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS uploaded_images (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id      UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    file_name       TEXT NOT NULL,
    file_path       TEXT NOT NULL,
        -- Path within Supabase Storage bucket
    content_type    TEXT NOT NULL DEFAULT 'image/jpeg',
    file_size_bytes BIGINT,
    public_url      TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);


-- ---------------------------------------------------------
-- Enable Row Level Security (recommended for Supabase)
-- For a hackathon prototype, we'll use permissive policies.
-- Tighten these for production.
-- ---------------------------------------------------------
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploaded_images ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated and anonymous users (hackathon mode)
CREATE POLICY "Allow all on sessions" ON sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on case_history" ON case_history FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on uploaded_images" ON uploaded_images FOR ALL USING (true) WITH CHECK (true);


-- ---------------------------------------------------------
-- Storage bucket for uploaded images
-- Run this separately if needed (Supabase may require using the dashboard)
-- ---------------------------------------------------------
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('defect-images', 'defect-images', true);
