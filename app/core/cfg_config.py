from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    CORE_BACKEND_URL: str = "http://localhost:8001"
    # BD del nucleo bancario para el puente de promocion (sync_outbox -> core)
    CORE_DATABASE_URL: str = (
        "postgresql://postgres:123456789@localhost:5432/bd_core_financiero"
    )
    # Forzar SSL en las conexiones PostgreSQL.
    # Render y Supabase lo requieren (`require`); para desarrollo local sin SSL
    # se puede usar `disable` o dejar la variable vacia.
    DB_USE_SSL: str = "require"
    CORE_DB_USE_SSL: str = "require"
    PORT: int = 8003

    class Config:
        env_file = ".env"


settings = Settings()
