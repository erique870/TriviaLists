import os
from pathlib import Path


def _load_env_file() -> None:
    env_file = Path(".env")
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k not in os.environ:
                os.environ[k] = v


_load_env_file()


def _clean_db_url(url: str) -> str:
    # Remove prefixos de ORMs específicos (ex: +asyncpg) para compatibilidade nativa com psycopg
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://", "postgres+asyncpg://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


class Settings:
    DATABASE_URL: str = _clean_db_url(os.getenv(
        "DATABASE_URL",
        "postgresql://trivialists:trivialists@localhost:5432/trivialists",
    ))
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "trivialists_secret_jwt_key_impatech_development_change_in_prod",
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))


settings = Settings()
