import logging
import time
from datetime import datetime, timezone

import requests
from requests.exceptions import HTTPError

from src.config import settings

logger = logging.getLogger(__name__)

# Browser-like headers so Yahoo treats our requests as normal traffic.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# Yahoo Finance v8 chart API — the same endpoint their website calls internally.
# We use this directly instead of the yfinance library because yfinance has
# issues with request handling inside Docker containers (ignores custom sessions).
_CHART_URL = "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"

# Map config period strings to Yahoo API range values
_PERIOD_MAP = {"1y": "1y", "2y": "2y", "5y": "5y"}


class StockDataFetcher:
    """
    Fetches stock OHLCV history and metadata from Yahoo Finance's chart API
    in a single request, returning data in a format ready for database insertion.
    """

    def fetch_stock_data(
        self, symbol: str, max_retries: int = 3, retry_delay: int = 30
    ) -> dict:
        """
        Fetch OHLCV data AND metadata in a single API call.

        Yahoo's chart API returns both price history and stock metadata in one
        response, so there's no need for separate requests. This avoids rate
        limiting caused by rapid back-to-back calls.

        Returns: {
            "records": [{"symbol": "AAPL", "date": date, "open": 150.0, ...}, ...],
            "meta": {"symbol": "AAPL", "name": "Apple Inc.", "sector": None, "currency": "USD"}
        }
        """
        url = _CHART_URL.format(symbol=symbol.upper())
        params = {
            "range": _PERIOD_MAP.get(settings.DEFAULT_HISTORY_PERIOD, "2y"),
            "interval": "1d",
        }

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(retry_delay)

                resp = requests.get(url, params=params, headers=_HEADERS, timeout=30)
                resp.raise_for_status()
                data = resp.json()

                # Yahoo's chart API response structure:
                # { "chart": { "result": [{ "meta": {...}, "timestamp": [...], "indicators": {"quote": [{"open": [...], ...}]} }] } }
                result = data["chart"]["result"]
                if not result:
                    raise ValueError(f"No chart data returned for {symbol}")

                chart = result[0]
                timestamps = chart["timestamp"]
                ohlcv = chart["indicators"]["quote"][0]
                raw_meta = chart["meta"]

                # Extract metadata from the same response
                meta = {
                    "symbol": symbol.upper(),
                    "name": raw_meta.get("longName") or raw_meta.get("shortName"),
                    "sector": None,
                    "currency": raw_meta.get("currency"),
                }

                # Build OHLCV records
                records = []
                for i, ts in enumerate(timestamps):
                    # Skip entries with None values (market holidays, data gaps)
                    if any(ohlcv[k][i] is None for k in ("open", "high", "low", "close", "volume")):
                        continue

                    records.append(
                        {
                            "symbol": symbol.upper(),
                            "date": datetime.fromtimestamp(ts, tz=timezone.utc).date(),
                            "open": round(float(ohlcv["open"][i]), 4),
                            "high": round(float(ohlcv["high"][i]), 4),
                            "low": round(float(ohlcv["low"][i]), 4),
                            "close": round(float(ohlcv["close"][i]), 4),
                            "volume": int(ohlcv["volume"][i]),
                        }
                    )

                logger.info(f"Fetched {len(records)} days of OHLCV for {symbol}")
                return {"records": records, "meta": meta}

            except HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    logger.warning(
                        f"Rate limited by Yahoo Finance, attempt {attempt + 1}/{max_retries}"
                    )
                    if attempt == max_retries - 1:
                        raise
                    continue
                raise

            except Exception as e:
                logger.error(
                    f"Error fetching data for {symbol} (attempt {attempt + 1}): {e}"
                )
                if attempt == max_retries - 1:
                    raise
                continue