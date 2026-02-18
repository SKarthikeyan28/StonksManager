import logging
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy.dialects.postgresql import insert

from src.config import settings
from src.database import Base, SessionLocal, engine
from src.fetcher import StockDataFetcher
from src.cache import cache_ohlcv
from src.models import StockMeta, StockPrice

logger = logging.getLogger(__name__)

# Create the Celery app instance.
# The first argument ("data_service") is the app name — used in logs and monitoring.
# broker= tells Celery where the message queue lives (Redis).
# backend= tells Celery where to store task results (return values, status).
# We use Redis for both broker and backend — broker handles the message queue,
# backend stores the results so callers can retrieve them via result.get().
celery_app = Celery("data_service", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

# Route tasks to the "data" queue so only data-workers pick them up.
# We match the explicit task name ("fetch_stock_data"), not the module path,
# because @celery_app.task(name="fetch_stock_data") overrides the auto-generated name.
celery_app.conf.task_routes = {
    "fetch_stock_data": {"queue": "data"},
}

fetcher = StockDataFetcher()


def _ensure_tables():
    """
    Create database tables if they don't exist yet.
    Safe to call multiple times — create_all() is a no-op if tables already exist.
    In production, you'd use Alembic migrations instead, but for initial development
    this gets us running without extra tooling.
    """
    Base.metadata.create_all(bind=engine)


@celery_app.task(name="fetch_stock_data")
def fetch_stock_data(symbol: str) -> dict:
    """
    Main Celery task: fetch stock data from Yahoo Finance, store in PostgreSQL,
    and cache in Redis.

    This is what gets called when the gateway dispatches:
        fetch_stock_data.delay("AAPL")

    Returns a summary dict so the gateway can report task status.
    """
    symbol = symbol.upper()
    logger.info(f"Starting data fetch for {symbol}")

    _ensure_tables()
    session = SessionLocal()

    try:
        # --- 1. Fetch OHLCV + metadata in a single API call ---
        # We use one request to get both price history and stock metadata.
        # This avoids Yahoo Finance rate limiting from rapid back-to-back calls.
        result = fetcher.fetch_stock_data(symbol)
        records = result["records"]
        meta = result["meta"]

        # --- 2. Upsert metadata ---
        meta_stmt = insert(StockMeta).values(
            symbol=meta["symbol"],
            name=meta["name"],
            sector=meta["sector"],
            currency=meta["currency"],
            last_fetched=datetime.now(timezone.utc),
        ).on_conflict_do_update(
            index_elements=["symbol"],
            set_={
                "name": meta["name"],
                "sector": meta["sector"],
                "currency": meta["currency"],
                "last_fetched": datetime.now(timezone.utc),
            },
        )
        session.execute(meta_stmt)

        # --- 3. Upsert OHLCV data ---

        # Bulk upsert: insert all rows, skip any that already exist (same symbol+date).
        # ON CONFLICT DO UPDATE ensures we overwrite with the latest data — Yahoo Finance
        # occasionally adjusts historical prices (stock splits, corrections).
        for record in records:
            price_stmt = insert(StockPrice).values(**record).on_conflict_do_update(
                index_elements=["symbol", "date"],
                set_={
                    "open": record["open"],
                    "high": record["high"],
                    "low": record["low"],
                    "close": record["close"],
                    "volume": record["volume"],
                },
            )
            session.execute(price_stmt)

        session.commit()
        logger.info(f"Persisted {len(records)} OHLCV records for {symbol} to PostgreSQL")

        # --- 3. Cache to Redis ---
        cache_ohlcv(symbol, records)

        return {
            "symbol": symbol,
            "records_count": len(records),
            "meta": meta,
            "status": "success",
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to fetch data for {symbol}: {e}")
        raise

    finally:
        # Always close the session to return the connection to the pool.
        # Without this, connections leak and eventually the pool is exhausted.
        session.close()
