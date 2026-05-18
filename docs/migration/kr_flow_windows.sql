-- Added 2026-05-19 (swing-main-b9p3).
-- Normalize KR investor flow storage:
--   - foreigner/institution/retail are the primary 1d display fields.
--   - explicit 1d/3d/10d windows preserve timing context for scan archive,
--     top-deep reports, Discord, and retraining.
ALTER TABLE market_scan_results
ADD COLUMN IF NOT EXISTS foreigner_1d numeric,
ADD COLUMN IF NOT EXISTS institution_1d numeric,
ADD COLUMN IF NOT EXISTS retail_1d numeric,
ADD COLUMN IF NOT EXISTS foreigner_3d numeric,
ADD COLUMN IF NOT EXISTS institution_3d numeric,
ADD COLUMN IF NOT EXISTS retail_3d numeric,
ADD COLUMN IF NOT EXISTS foreigner_10d numeric,
ADD COLUMN IF NOT EXISTS institution_10d numeric,
ADD COLUMN IF NOT EXISTS retail_10d numeric,
ADD COLUMN IF NOT EXISTS whale_flow_1d numeric,
ADD COLUMN IF NOT EXISTS whale_flow_3d numeric,
ADD COLUMN IF NOT EXISTS whale_flow_10d numeric,
ADD COLUMN IF NOT EXISTS flow_window text,
ADD COLUMN IF NOT EXISTS flow_asof text;
