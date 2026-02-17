from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Central configuration loaded from environment variables.
    Pydantic validates these at startup — if DATABASE_URL is missing,
    you get a clear error instead of a runtime crash later.
    """

    DATABASE_URL: str = "postgresql://stonks:stonks_dev@localhost:5432/stonksmanager"
    REDIS_URL: str = "redis://localhost:6379/0"

    # yfinance: how far back to fetch historical data
    DEFAULT_HISTORY_PERIOD: str = "2y"

    # Redis cache TTL in seconds (1 hour default)
    CACHE_TTL: int = 3600

    class Config:
        env_file = ".env"


settings = Settings()
