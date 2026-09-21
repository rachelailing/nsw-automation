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
    state           JSONB DEFAULT '{}'::jsonb,
        -- Full orchestrator state, including pending questions and intermediate agent outputs
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
-- Reference Thresholds: Deterministic numeric parameter checks
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS reference_thresholds (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    material            TEXT,
    defect_type         TEXT,
    target_volume       NUMERIC,
    min_volume          NUMERIC,
    max_volume          NUMERIC,
    target_pressure     NUMERIC,
    min_pressure        NUMERIC,
    max_pressure        NUMERIC,
    target_speed        NUMERIC,
    min_speed           NUMERIC,
    max_speed           NUMERIC,
    target_time         NUMERIC,
    min_time            NUMERIC,
    max_time            NUMERIC,
    target_nozzle_size  NUMERIC,
    min_nozzle_size     NUMERIC,
    max_nozzle_size     NUMERIC,
    target_height       NUMERIC,
    min_height          NUMERIC,
    max_height          NUMERIC,
    target_diameter_mm  NUMERIC,
    min_diameter_mm     NUMERIC,
    max_diameter_mm     NUMERIC,
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE reference_thresholds
    ADD COLUMN IF NOT EXISTS target_diameter_mm NUMERIC,
    ADD COLUMN IF NOT EXISTS min_diameter_mm NUMERIC,
    ADD COLUMN IF NOT EXISTS max_diameter_mm NUMERIC;

CREATE INDEX IF NOT EXISTS idx_reference_thresholds_material
    ON reference_thresholds(material);

CREATE INDEX IF NOT EXISTS idx_reference_thresholds_defect_type
    ON reference_thresholds(defect_type);

INSERT INTO reference_thresholds (
    material,
    defect_type,
    target_pressure,
    min_pressure,
    max_pressure,
    target_time,
    min_time,
    max_time,
    target_nozzle_size,
    min_nozzle_size,
    max_nozzle_size,
    notes
)
SELECT
    'silver epoxy adhesive',
    'Undersized Dot',
    0.32,
    0.30,
    0.35,
    80,
    75,
    90,
    200,
    180,
    220,
    'Demo thresholds for silver epoxy dot dispensing.'
WHERE NOT EXISTS (
    SELECT 1
    FROM reference_thresholds
    WHERE material = 'silver epoxy adhesive'
      AND defect_type = 'Undersized Dot'
);

INSERT INTO reference_thresholds (
    material,
    defect_type,
    target_pressure,
    min_pressure,
    max_pressure,
    target_time,
    min_time,
    max_time,
    target_nozzle_size,
    min_nozzle_size,
    max_nozzle_size,
    notes
)
SELECT
    'generic adhesive',
    NULL,
    0.32,
    0.28,
    0.36,
    80,
    70,
    95,
    200,
    150,
    250,
    'Fallback demo thresholds when material or defect type is unknown.'
WHERE NOT EXISTS (
    SELECT 1
    FROM reference_thresholds
    WHERE material = 'generic adhesive'
      AND defect_type IS NULL
);
INSERT INTO reference_thresholds (
    material,
    target_diameter_mm,
    min_diameter_mm,
    max_diameter_mm,
    notes
)
SELECT
    'silver epoxy adhesive',
    0.45,
    0.40,
    0.50,
    'Standard dot diameter limits in mm.'
WHERE NOT EXISTS (
    SELECT 1
    FROM reference_thresholds
    WHERE material = 'silver epoxy adhesive'
      AND target_diameter_mm = 0.45
);

INSERT INTO reference_thresholds (
    material,
    target_diameter_mm,
    min_diameter_mm,
    max_diameter_mm,
    notes
)
SELECT
    'solder paste',
    0.50,
    0.40,
    0.60,
    'Demo dot diameter limits matching the n8n workflow.'
WHERE NOT EXISTS (
    SELECT 1
    FROM reference_thresholds
    WHERE material = 'solder paste'
      AND target_diameter_mm = 0.50
);


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
ALTER TABLE reference_thresholds ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated and anonymous users (hackathon mode)
CREATE POLICY "Allow all on sessions" ON sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on case_history" ON case_history FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on uploaded_images" ON uploaded_images FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all on reference_thresholds" ON reference_thresholds FOR ALL USING (true) WITH CHECK (true);


-- ---------------------------------------------------------
-- Storage bucket for uploaded images
-- Run this separately if needed (Supabase may require using the dashboard)
-- ---------------------------------------------------------
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('defect-images', 'defect-images', true);
