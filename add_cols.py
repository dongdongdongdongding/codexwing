import requests
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

query = """
ALTER TABLE market_scan_results 
ADD COLUMN IF NOT EXISTS tier text,
ADD COLUMN IF NOT EXISTS volume text,
ADD COLUMN IF NOT EXISTS context text,
ADD COLUMN IF NOT EXISTS surge text,
ADD COLUMN IF NOT EXISTS win_rate text,
ADD COLUMN IF NOT EXISTS position text,
ADD COLUMN IF NOT EXISTS strategy text,
ADD COLUMN IF NOT EXISTS decision_score numeric;
"""

# Let's try running the query through the pg REST endpoint, if not available, we can't alter it directly without postgres connection string
import psycopg2
# The user doesn't have the direct DB string in env out of the box (only REST URL/KEY usually). 
# Let's check environment vars.
