-- Run this in your Supabase SQL Editor:
ALTER TABLE market_scan_results 
ADD COLUMN IF NOT EXISTS tier text,
ADD COLUMN IF NOT EXISTS volume text,
ADD COLUMN IF NOT EXISTS context text,
ADD COLUMN IF NOT EXISTS surge text,
ADD COLUMN IF NOT EXISTS win_rate text,
ADD COLUMN IF NOT EXISTS position text,
ADD COLUMN IF NOT EXISTS strategy text,
ADD COLUMN IF NOT EXISTS decision_score numeric;
