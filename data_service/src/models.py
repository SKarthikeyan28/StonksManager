from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Date, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class StockMeta(Base):
    """
    One row per stock symbol. Tracks metadata and when we last fetched data,
    so we can avoid redundant yfinance calls.
    """

    __tablename__ = "stock_meta"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    sector: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str | None] = mapped_column(String(10))
    last_fetched: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class StockPrice(Base):
    """
    One row per symbol per day — OHLCV data.
    Composite primary key (symbol + date) because a symbol can have many dates,
    and a date can have many symbols, but each combination is unique.
    This table will be converted to a TimescaleDB hypertable for fast time-range queries.
    """

    __tablename__ = "stock_prices"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    date: Mapped[datetime] = mapped_column(Date, primary_key=True)
    open: Mapped[float] = mapped_column(Numeric(14, 4))
    high: Mapped[float] = mapped_column(Numeric(14, 4))
    low: Mapped[float] = mapped_column(Numeric(14, 4))
    close: Mapped[float] = mapped_column(Numeric(14, 4))
    volume: Mapped[int] = mapped_column(BigInteger)
