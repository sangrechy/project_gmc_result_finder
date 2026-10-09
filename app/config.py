import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "35.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF_SECONDS = float(os.getenv("RETRY_BACKOFF_SECONDS", "1.5"))
BATCH_CONCURRENCY = int(os.getenv("BATCH_CONCURRENCY", "3"))

CACHE_DB_PATH = DATA_DIR / "results_cache.db"
DEFAULT_CACHE_TTL_SECONDS = int(os.getenv("DEFAULT_CACHE_TTL_SECONDS", str(7 * 24 * 3600)))
MEMORY_CACHE_MAX_SIZE = int(os.getenv("MEMORY_CACHE_MAX_SIZE", "500"))
