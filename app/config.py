import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


class Settings:
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'tracelink.db'}")

    # random secret if none is set (tokens stop working after a restart)
    jwt_secret: str = os.getenv("JWT_SECRET") or secrets.token_urlsafe(48)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

    bootstrap_username: str = os.getenv("BOOTSTRAP_USERNAME", "admin")
    bootstrap_password: str = os.getenv("BOOTSTRAP_PASSWORD", "admin123")

    # inline = process inside the request, redis = queue + worker.py
    queue_mode: str = os.getenv("QUEUE_MODE", "inline")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    stats_cache_seconds: int = int(os.getenv("STATS_CACHE_SECONDS", "30"))

    model_path: Path = BASE_DIR / "models" / "classifier.joblib"
    training_data_path: Path = BASE_DIR / "data" / "synthetic_complaints.csv"

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


settings = Settings()
