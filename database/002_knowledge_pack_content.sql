-- Structured Knowledge Pack content migration.
-- Requires projects, knowledge_packs, and knowledge_sources from schema.sql.

CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_sources_pack_name
    ON knowledge_sources(knowledge_pack_id, source_name);

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

INSERT INTO knowledge_sources (
    knowledge_pack_id,
    source_name,
    source_type,
    extraction_status,
    uploaded_by
)
SELECT
    kp.id,
    'Prototype dispensing expert rules v1',
    'internal_expert_seed',
    'completed',
    'system'
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

ALTER TABLE materials ENABLE ROW LEVEL SECURITY;
ALTER TABLE defect_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE troubleshooting_actions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all on materials" ON materials;
CREATE POLICY "Allow all on materials"
    ON materials FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all on defect_rules" ON defect_rules;
CREATE POLICY "Allow all on defect_rules"
    ON defect_rules FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all on troubleshooting_actions" ON troubleshooting_actions;
CREATE POLICY "Allow all on troubleshooting_actions"
    ON troubleshooting_actions FOR ALL USING (true) WITH CHECK (true);

SELECT 'materials' AS content_type, COUNT(*) AS records
FROM materials
WHERE knowledge_pack_id = 1
UNION ALL
SELECT 'defect_rules', COUNT(*)
FROM defect_rules
WHERE knowledge_pack_id = 1
UNION ALL
SELECT 'troubleshooting_actions', COUNT(*)
FROM troubleshooting_actions
WHERE knowledge_pack_id = 1;
