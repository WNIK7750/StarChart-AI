from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[3]
DATABASE_PATH = BASE_DIR / "database" / "ai_nav.sqlite3"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
SEED_PATH = BASE_DIR / "database" / "seed.sql"
LEARNING_CONTENT_PATH = BASE_DIR / "database" / "learning_content.sql"
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOAD_DIR = BASE_DIR / "uploads"

API_PREFIX = "/api/v1"
APP_NAME = "AI Knowledge Navigation API"
SECRET_KEY = os.getenv("AI_NAV_SECRET_KEY", "dev-secret-change-before-production")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14"))
RESET_DATABASE_ON_START = os.getenv("RESET_DATABASE_ON_START", "0") == "1"
AVATAR_MAX_UPLOAD_BYTES = int(os.getenv("AVATAR_MAX_UPLOAD_BYTES", str(2 * 1024 * 1024)))
AVATAR_MAX_OUTPUT_BYTES = int(os.getenv("AVATAR_MAX_OUTPUT_BYTES", str(360 * 1024)))
AVATAR_MAX_DIMENSION = int(os.getenv("AVATAR_MAX_DIMENSION", "512"))
