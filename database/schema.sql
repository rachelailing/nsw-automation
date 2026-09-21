-- ============================================================
-- AI Dispensing Defect Detective — Database Schema
-- Run this in Supabase SQL Editor to create the required tables.
-- ============================================================

-- ---------------------------------------------------------
-- Projects: Scope knowledge to a machine, line, or product
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    machine_name    TEXT,
    production_line TEXT,
    product_name    TEXT,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ---------------------------------------------------------
-- Knowledge Packs: Versioned, approved troubleshooting knowledge
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_packs (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id      BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    version         INTEGER NOT NULL CHECK (version > 0),
    status          TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'in_review', 'approved', 'superseded', 'archived')),
    description     TEXT,
    created_by      TEXT,
    approved_by     TEXT,
    approved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, name, version)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_packs_project
    ON knowledge_packs(project_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_packs_status
    ON knowledge_packs(status);

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_approved_knowledge_pack
    ON knowledge_packs(project_id, name)
    WHERE status = 'approved';


-- ---------------------------------------------------------
-- Knowledge Sources: Documents and references used by a pack
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_sources (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    knowledge_pack_id   BIGINT NOT NULL REFERENCES knowledge_packs(id) ON DELETE CASCADE,
    source_name         TEXT NOT NULL,
    source_type         TEXT NOT NULL,
    source_uri          TEXT,
    storage_path        TEXT,
    checksum            TEXT,
    original_filename   TEXT,
    file_size_bytes     BIGINT,
    extracted_text      TEXT,
    extracted_content   JSONB,
    extraction_status   TEXT NOT NULL DEFAULT 'not_started'
        CHECK (extraction_status IN ('not_started', 'processing', 'completed', 'failed')),
    review_status       TEXT NOT NULL DEFAULT 'pending_review'
        CHECK (review_status IN ('pending_review', 'approved', 'rejected')),
    error_message       TEXT,
    uploaded_by         TEXT,
    reviewed_by         TEXT,
    reviewed_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE knowledge_sources
    ADD COLUMN IF NOT EXISTS original_filename TEXT,
    ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT,
    ADD COLUMN IF NOT EXISTS extracted_text TEXT,
    ADD COLUMN IF NOT EXISTS extracted_content JSONB,
    ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'pending_review',
    ADD COLUMN IF NOT EXISTS error_message TEXT,
    ADD COLUMN IF NOT EXISTS reviewed_by TEXT,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_knowledge_sources_pack
    ON knowledge_sources(knowledge_pack_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_sources_pack_name
    ON knowledge_sources(knowledge_pack_id, source_name);


-- ---------------------------------------------------------
-- Materials: Approved material properties and handling facts
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS materials (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    knowledge_pack_id   BIGINT NOT NULL REFERENCES knowledge_packs(id) ON DELETE CASCADE,
    source_id           BIGINT REFERENCES knowledge_sources(id) ON DELETE SET NULL,
    name                TEXT NOT NULL,
    aliases             TEXT[] NOT NULL DEFAULT '{}',
    material_type       TEXT,
    viscosity_min       NUMERIC,
    viscosity_max       NUMERIC,
    viscosity_unit      TEXT,
    handling_notes      TEXT,
    storage_conditions  TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (knowledge_pack_id, name)
);

CREATE INDEX IF NOT EXISTS idx_materials_pack
    ON materials(knowledge_pack_id);


-- ---------------------------------------------------------
-- Defect Rules: Expert-authored defect-to-cause evidence
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS defect_rules (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    knowledge_pack_id   BIGINT NOT NULL REFERENCES knowledge_packs(id) ON DELETE CASCADE,
    source_id           BIGINT REFERENCES knowledge_sources(id) ON DELETE SET NULL,
    defect_type         TEXT NOT NULL,
    conditions          JSONB NOT NULL DEFAULT '{}'::jsonb,
    possible_cause      TEXT NOT NULL,
    category            TEXT NOT NULL,
    reasoning           TEXT NOT NULL,
    evidence_weight     NUMERIC NOT NULL DEFAULT 0.5
        CHECK (evidence_weight >= 0 AND evidence_weight <= 1),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (knowledge_pack_id, defect_type, possible_cause)
);

CREATE INDEX IF NOT EXISTS idx_defect_rules_pack_defect
    ON defect_rules(knowledge_pack_id, defect_type);


-- ---------------------------------------------------------
-- Troubleshooting Actions: Approved and ordered checks/fixes
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS troubleshooting_actions (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    knowledge_pack_id   BIGINT NOT NULL REFERENCES knowledge_packs(id) ON DELETE CASCADE,
    source_id           BIGINT REFERENCES knowledge_sources(id) ON DELETE SET NULL,
    defect_type         TEXT NOT NULL,
    cause               TEXT NOT NULL,
    action              TEXT NOT NULL,
    sequence            INTEGER NOT NULL CHECK (sequence > 0),
    safety_notes        TEXT,
    requires_approval   BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (knowledge_pack_id, defect_type, cause, sequence)
);

CREATE INDEX IF NOT EXISTS idx_actions_pack_defect
    ON troubleshooting_actions(knowledge_pack_id, defect_type, sequence);


-- Seed one approved pack for the existing prototype data.
INSERT INTO projects (
    name,
    machine_name,
    production_line,
    product_name,
    description
)
VALUES (
    'Demo Dispensing Project',
    'Demo Dispensing Machine',
    'Demo Line',
    'Solder Paste Assembly',
    'Initial project for the dispensing-defect prototype.'
)
ON CONFLICT (name) DO NOTHING;

INSERT INTO knowledge_packs (
    project_id,
    name,
    version,
    status,
    description,
    created_by,
    approved_by,
    approved_at
)
SELECT
    id,
    'Standard Dispensing Knowledge',
    1,
    'approved',
    'Initial approved thresholds and troubleshooting knowledge.',
    'system',
    'prototype-admin',
    now()
FROM projects
WHERE name = 'Demo Dispensing Project'
ON CONFLICT (project_id, name, version) DO NOTHING;

INSERT INTO knowledge_sources (
    knowledge_pack_id,
    source_name,
    source_type,
    extraction_status,
    review_status,
    uploaded_by,
    reviewed_by,
    reviewed_at
)
SELECT
    kp.id,
    'Prototype dispensing expert rules v1',
    'internal_expert_seed',
    'completed',
    'approved',
    'system',
    'prototype-admin',
    now()
FROM knowledge_packs kp
JOIN projects p ON p.id = kp.project_id
WHERE p.name = 'Demo Dispensing Project'
  AND kp.name = 'Standard Dispensing Knowledge'
  AND kp.version = 1
ON CONFLICT (knowledge_pack_id, source_name) DO NOTHING;

INSERT INTO materials (
    knowledge_pack_id,
    source_id,
    name,
    aliases,
    material_type,
    handling_notes,
    storage_conditions
)
SELECT
    kp.id,
    ks.id,
    'Solder Paste',
    ARRAY['soldering paste', 'paste'],
    'Solder paste',
    'Bring material to the approved process temperature and mix only according to the supplier procedure.',
    'Follow the supplier shelf-life, refrigeration, and exposure-time requirements.'
FROM knowledge_packs kp
JOIN projects p ON p.id = kp.project_id
JOIN knowledge_sources ks
  ON ks.knowledge_pack_id = kp.id
 AND ks.source_name = 'Prototype dispensing expert rules v1'
WHERE p.name = 'Demo Dispensing Project'
  AND kp.name = 'Standard Dispensing Knowledge'
  AND kp.version = 1
ON CONFLICT (knowledge_pack_id, name) DO NOTHING;

INSERT INTO defect_rules (
    knowledge_pack_id,
    source_id,
    defect_type,
    conditions,
    possible_cause,
    category,
    reasoning,
    evidence_weight
)
SELECT kp.id, ks.id, v.*
FROM knowledge_packs kp
JOIN projects p ON p.id = kp.project_id
JOIN knowledge_sources ks
  ON ks.knowledge_pack_id = kp.id
 AND ks.source_name = 'Prototype dispensing expert rules v1'
CROSS JOIN (VALUES
    ('Oversized Dot', '{"frequency":"continuous"}'::jsonb, 'Dispensing pressure or dispensing time is too high', 'Dispensing Parameters', 'Continuous oversized deposits are consistent with excessive delivered volume.', 0.90),
    ('Oversized Dot', '{}'::jsonb, 'Nozzle inner diameter is larger than the approved recipe', 'Nozzle Condition', 'A larger nozzle can increase deposited volume when other settings remain unchanged.', 0.75),
    ('Oversized Dot', '{"frequency":"intermittent"}'::jsonb, 'Material viscosity or temperature is unstable', 'Material Condition', 'Intermittent size variation can follow changes in material flow behavior.', 0.60),
    ('Undersized Dot', '{"frequency":"continuous"}'::jsonb, 'Dispensing pressure or dispensing time is too low', 'Dispensing Parameters', 'Continuous undersized deposits are consistent with insufficient delivered volume.', 0.90),
    ('Undersized Dot', '{}'::jsonb, 'Nozzle is partially blocked or worn', 'Nozzle Condition', 'A restricted material path can reduce deposited volume.', 0.80),
    ('Undersized Dot', '{"frequency":"intermittent"}'::jsonb, 'Air is trapped in the syringe or material path', 'Air Bubbles', 'Compressible air can cause intermittent short shots.', 0.75)
) AS v(defect_type, conditions, possible_cause, category, reasoning, evidence_weight)
WHERE p.name = 'Demo Dispensing Project'
  AND kp.name = 'Standard Dispensing Knowledge'
  AND kp.version = 1
ON CONFLICT (knowledge_pack_id, defect_type, possible_cause) DO NOTHING;

INSERT INTO troubleshooting_actions (
    knowledge_pack_id,
    source_id,
    defect_type,
    cause,
    action,
    sequence,
    safety_notes,
    requires_approval
)
SELECT kp.id, ks.id, v.*
FROM knowledge_packs kp
JOIN projects p ON p.id = kp.project_id
JOIN knowledge_sources ks
  ON ks.knowledge_pack_id = kp.id
 AND ks.source_name = 'Prototype dispensing expert rules v1'
CROSS JOIN (VALUES
    ('Oversized Dot', 'Dispensing pressure or dispensing time is too high', 'Verify pressure and dispensing time against the approved recipe, then reduce only one parameter in a controlled trial.', 1, 'Remain within the qualified process window.', true),
    ('Oversized Dot', 'Nozzle inner diameter is larger than the approved recipe', 'Confirm the installed nozzle part number and inner diameter against the approved recipe.', 2, NULL, false),
    ('Oversized Dot', 'Material viscosity or temperature is unstable', 'Confirm material temperature, exposure time, and mixing history before dispensing another sample.', 3, 'Follow the supplier handling procedure.', false),
    ('Undersized Dot', 'Dispensing pressure or dispensing time is too low', 'Verify pressure and dispensing time against the approved recipe, then increase only one parameter in a controlled trial.', 1, 'Remain within the qualified process window.', true),
    ('Undersized Dot', 'Nozzle is partially blocked or worn', 'Inspect the nozzle and replace it with a verified nozzle if blockage or wear is found.', 2, 'Depressurize the dispensing system before nozzle service.', false),
    ('Undersized Dot', 'Air is trapped in the syringe or material path', 'Inspect for trapped air and reload or degas the material using the approved procedure.', 3, 'Follow the material handling and equipment safety procedure.', false)
) AS v(defect_type, cause, action, sequence, safety_notes, requires_approval)
WHERE p.name = 'Demo Dispensing Project'
  AND kp.name = 'Standard Dispensing Knowledge'
  AND kp.version = 1
ON CONFLICT (knowledge_pack_id, defect_type, cause, sequence) DO NOTHING;


-- ---------------------------------------------------------
-- Sessions: Active conversation state per user
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id      BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    knowledge_pack_id BIGINT REFERENCES knowledge_packs(id) ON DELETE SET NULL,
    session_id      UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    step            TEXT NOT NULL DEFAULT 'questioning',
        -- Possible values include questioning, ranking, reporting, awaiting_feedback, closed
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

ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS project_id BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS knowledge_pack_id BIGINT REFERENCES knowledge_packs(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_sessions_project
    ON sessions(project_id);

CREATE INDEX IF NOT EXISTS idx_sessions_knowledge_pack
    ON sessions(knowledge_pack_id);

-- Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS projects_updated_at ON projects;
CREATE TRIGGER projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS knowledge_packs_updated_at ON knowledge_packs;
CREATE TRIGGER knowledge_packs_updated_at
    BEFORE UPDATE ON knowledge_packs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS sessions_updated_at ON sessions;
CREATE TRIGGER sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ---------------------------------------------------------
-- Case History: Completed cases for RAG / learning database
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_history (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id      BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    knowledge_pack_id BIGINT REFERENCES knowledge_packs(id) ON DELETE SET NULL,
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

ALTER TABLE case_history
    ADD COLUMN IF NOT EXISTS project_id BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS knowledge_pack_id BIGINT REFERENCES knowledge_packs(id) ON DELETE SET NULL;

-- Index for RAG lookups: find similar cases by defect type
CREATE INDEX IF NOT EXISTS idx_case_history_defect_type
    ON case_history(defect_type);

-- Index for ordering by recency
CREATE INDEX IF NOT EXISTS idx_case_history_created_at
    ON case_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_case_history_project
    ON case_history(project_id);

CREATE INDEX IF NOT EXISTS idx_case_history_knowledge_pack
    ON case_history(knowledge_pack_id);


-- ---------------------------------------------------------
-- Case Feedback: Confirmed outcomes from technician testing
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS case_feedback (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id             BIGINT NOT NULL REFERENCES case_history(id) ON DELETE CASCADE,
    session_id          UUID REFERENCES sessions(session_id) ON DELETE SET NULL,
    fixed               BOOLEAN NOT NULL,
    attempted_action    TEXT NOT NULL,
    confirmed_cause     TEXT,
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE case_feedback
    ADD COLUMN IF NOT EXISTS notes TEXT;

CREATE INDEX IF NOT EXISTS idx_case_feedback_case_id
    ON case_feedback(case_id);

CREATE INDEX IF NOT EXISTS idx_case_feedback_session_id
    ON case_feedback(session_id);


-- ---------------------------------------------------------
-- Reference Thresholds: Deterministic numeric parameter checks
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS reference_thresholds (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id          BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    knowledge_pack_id   BIGINT REFERENCES knowledge_packs(id) ON DELETE SET NULL,
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
    ADD COLUMN IF NOT EXISTS max_diameter_mm NUMERIC,
    ADD COLUMN IF NOT EXISTS project_id BIGINT REFERENCES projects(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS knowledge_pack_id BIGINT REFERENCES knowledge_packs(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_reference_thresholds_material
    ON reference_thresholds(material);

CREATE INDEX IF NOT EXISTS idx_reference_thresholds_defect_type
    ON reference_thresholds(defect_type);

CREATE INDEX IF NOT EXISTS idx_reference_thresholds_project
    ON reference_thresholds(project_id);

CREATE INDEX IF NOT EXISTS idx_reference_thresholds_knowledge_pack
    ON reference_thresholds(knowledge_pack_id);

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


-- Link existing prototype records to the seeded approved Knowledge Pack.
UPDATE reference_thresholds
SET
    project_id = (
        SELECT id
        FROM projects
        WHERE name = 'Demo Dispensing Project'
    ),
    knowledge_pack_id = (
        SELECT kp.id
        FROM knowledge_packs kp
        JOIN projects p ON p.id = kp.project_id
        WHERE p.name = 'Demo Dispensing Project'
          AND kp.name = 'Standard Dispensing Knowledge'
          AND kp.version = 1
    )
WHERE project_id IS NULL OR knowledge_pack_id IS NULL;

UPDATE sessions
SET
    project_id = (
        SELECT id
        FROM projects
        WHERE name = 'Demo Dispensing Project'
    ),
    knowledge_pack_id = (
        SELECT kp.id
        FROM knowledge_packs kp
        JOIN projects p ON p.id = kp.project_id
        WHERE p.name = 'Demo Dispensing Project'
          AND kp.name = 'Standard Dispensing Knowledge'
          AND kp.version = 1
    )
WHERE project_id IS NULL OR knowledge_pack_id IS NULL;

UPDATE case_history
SET
    project_id = (
        SELECT id
        FROM projects
        WHERE name = 'Demo Dispensing Project'
    ),
    knowledge_pack_id = (
        SELECT kp.id
        FROM knowledge_packs kp
        JOIN projects p ON p.id = kp.project_id
        WHERE p.name = 'Demo Dispensing Project'
          AND kp.name = 'Standard Dispensing Knowledge'
          AND kp.version = 1
    )
WHERE project_id IS NULL OR knowledge_pack_id IS NULL;


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
ALTER TABLE case_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploaded_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE reference_thresholds ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_packs ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE materials ENABLE ROW LEVEL SECURITY;
ALTER TABLE defect_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE troubleshooting_actions ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated and anonymous users (hackathon mode)
DROP POLICY IF EXISTS "Allow all on sessions" ON sessions;
CREATE POLICY "Allow all on sessions" ON sessions FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all on case_history" ON case_history;
CREATE POLICY "Allow all on case_history" ON case_history FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all on case_feedback" ON case_feedback;
CREATE POLICY "Allow all on case_feedback" ON case_feedback FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all on uploaded_images" ON uploaded_images;
CREATE POLICY "Allow all on uploaded_images" ON uploaded_images FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all on reference_thresholds" ON reference_thresholds;
CREATE POLICY "Allow all on reference_thresholds" ON reference_thresholds FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all on projects" ON projects;
CREATE POLICY "Allow all on projects" ON projects FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all on knowledge_packs" ON knowledge_packs;
CREATE POLICY "Allow all on knowledge_packs" ON knowledge_packs FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all on knowledge_sources" ON knowledge_sources;
CREATE POLICY "Allow all on knowledge_sources" ON knowledge_sources FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all on materials" ON materials;
CREATE POLICY "Allow all on materials" ON materials FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all on defect_rules" ON defect_rules;
CREATE POLICY "Allow all on defect_rules" ON defect_rules FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all on troubleshooting_actions" ON troubleshooting_actions;
CREATE POLICY "Allow all on troubleshooting_actions" ON troubleshooting_actions FOR ALL USING (true) WITH CHECK (true);


-- ---------------------------------------------------------
-- Storage bucket for uploaded images
-- Run this separately if needed (Supabase may require using the dashboard)
-- ---------------------------------------------------------
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('defect-images', 'defect-images', true);
