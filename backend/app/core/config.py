from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[3]
DATABASE_PATH = BASE_DIR / "database" / "ai_nav.sqlite3"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
SEED_PATH = BASE_DIR / "database" / "seed.sql"
LEARNING_CONTENT_PATH = BASE_DIR / "database" / "learning_content.sql"
FRONTEND_DIR = BASE_DIR / "frontend"

API_PREFIX = "/api/v1"
APP_NAME = "AI Knowledge Navigation API"
