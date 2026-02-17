-- This script runs once when PostgreSQL first initializes (empty data directory).
-- It enables TimescaleDB and creates the schema for the data service.

-- Enable the TimescaleDB extension (pre-installed in the timescale/timescaledb image)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Static metadata: one row per stock symbol
CREATE TABLE IF NOT EXISTS stock_meta (
    symbol       VARCHAR(10) PRIMARY KEY,
    name         VARCHAR(255),
    sector       VARCHAR(100),
    currency     VARCHAR(10),
    last_fetched TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- OHLCV price data: one row per symbol per day
CREATE TABLE IF NOT EXISTS stock_prices (
    symbol  VARCHAR(10) NOT NULL,
    date    DATE NOT NULL,
    open    NUMERIC(14,4),
    high    NUMERIC(14,4),
    low     NUMERIC(14,4),
    close   NUMERIC(14,4),
    volume  BIGINT,
    PRIMARY KEY (symbol, date)
);

-- Convert stock_prices into a TimescaleDB hypertable, partitioned by date.
-- if_not_exists => TRUE makes this safe to re-run without errors.
SELECT create_hypertable('stock_prices', 'date', if_not_exists => TRUE);