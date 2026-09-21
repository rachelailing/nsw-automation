-- Add reviewable extraction fields for Knowledge Pack source imports.

ALTER TABLE knowledge_sources
    ADD COLUMN IF NOT EXISTS original_filename TEXT,
    ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT,
    ADD COLUMN IF NOT EXISTS extracted_text TEXT,
    ADD COLUMN IF NOT EXISTS extracted_content JSONB,
    ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'pending_review',
    ADD COLUMN IF NOT EXISTS error_message TEXT,
    ADD COLUMN IF NOT EXISTS reviewed_by TEXT,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

UPDATE knowledge_sources
SET review_status = 'approved',
    reviewed_by = COALESCE(reviewed_by, 'system'),
    reviewed_at = COALESCE(reviewed_at, created_at)
WHERE source_type = 'internal_expert_seed'
  AND review_status = 'pending_review';

SELECT
    id,
    source_name,
    extraction_status,
    review_status
FROM knowledge_sources
ORDER BY created_at DESC;
