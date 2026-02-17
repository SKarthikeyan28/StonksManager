import logging
import time

import yfinance as yf
from requests.exceptions import HTTPError

from src.config import settings

logger = logging.getLogger(__name__)


class StockDataFetcher:
    """
    Fetches stock data from Yahoo Finance - returns data in a format ready for database insertion.
        - fetch_ohlcv() gets historical price data (OHLCV) for a symbol.
        - fetch_meta() gets stock metadata (name, sector, currency).
    """

    def fetch_ohlcv(
        self, symbol: str, max_retries: int = 3, retry_delay: int = 5
    ) -> list[dict]:
        """
        Fetch historical OHLCV (Open, High, Low, Close, Volume) data.

        Returns a list of dicts, one per day:
        [{"symbol": "AAPL", "date": date, "open": 150.0, ...}, ...]

        Raises an exception on failure (Celery will handle the error).
        """
        ticker = yf.Ticker(symbol)

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(retry_delay)

                # .history() returns a pandas DataFrame with DatetimeIndex
                # columns: Open, High, Low, Close, Volume (+ Dividends, Stock Splits)
                df = ticker.history(period=settings.DEFAULT_HISTORY_PERIOD)

                if df.empty:
                    raise ValueError(f"No historical data returned for {symbol}")

                # Convert DataFrame rows into a list of dicts for bulk DB insert.
                # df.index is the date, df.columns are OHLCV fields.
                records = []
                for date, row in df.iterrows():
                    records.append(
                        {
                            "symbol": symbol.upper(),
                            "date": date.date(),
                            "open": round(float(row["Open"]), 4),
                            "high": round(float(row["High"]), 4),
                            "low": round(float(row["Low"]), 4),
                            "close": round(float(row["Close"]), 4),
                            "volume": int(row["Volume"]),
                        }
                    )

                #using logger instead of print statements for better control over logging output and levels
                logger.info(f"Fetched {len(records)} days of OHLCV for {symbol}")
                return records

            except HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    logger.warning(
                        f"Rate limited by Yahoo Finance, attempt {attempt + 1}/{max_retries}"
                    )
                    #include retries approach to handle rate limits gracefully, with delay between attempts
                    if attempt == max_retries - 1:
                        raise
                    continue
                raise

            except Exception as e:
                logger.error(
                    f"Error fetching OHLCV for {symbol} (attempt {attempt + 1}): {e}"
                )
                if attempt == max_retries - 1:
                    raise
                continue

    def fetch_meta(self, symbol: str) -> dict:
        """
        Fetch stock metadata (name, sector, currency).

        Returns a dict: {"symbol": "AAPL", "name": "Apple Inc.", ...}
        Fields may be None if Yahoo Finance doesn't have them.
        """
        ticker = yf.Ticker(symbol)
        info = ticker.info

        return {
            "symbol": symbol.upper(),
            "name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "currency": info.get("currency"),
        }
