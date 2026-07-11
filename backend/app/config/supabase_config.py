"""
Supabase Configuration for StrategAI
"""

import os
from pathlib import Path
from dotenv import dotenv_values

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
ENV_VALUES = {
    key.lstrip("\ufeff"): value
    for key, value in dotenv_values(ENV_PATH).items()
}

# Supabase PostgreSQL Connection
SUPABASE_URL = os.getenv("SUPABASE_URL") or ENV_VALUES.get("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or ENV_VALUES.get("SUPABASE_KEY", "")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL") or ENV_VALUES.get("SUPABASE_DB_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or ENV_VALUES.get("SUPABASE_SERVICE_KEY", "")

# Example format:
# postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
