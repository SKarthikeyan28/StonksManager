from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # SQLite path — the auth database lives inside the container
    DATABASE_URL: str = "sqlite:///./gateway.db"

    # Redis — used by Celery as both broker and result backend
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT settings
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    class Config:
        env_file = ".env"


settings = Settings()