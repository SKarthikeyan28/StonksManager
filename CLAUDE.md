# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Rules

- Always confirm with the user before writing code, editing files, or running terminal commands.
- When implementing changes, explain the reasoning behind each decision — why this approach, why this tool/library, and how it fits into the overall architecture. Treat this as a learning walkthrough, not just code delivery.

---

## Project Overview

StonksManager is a university/portfolio project — a microservices-based stock analysis platform. It combines Reddit sentiment analysis with stock price data, technical indicators, and price forecasting, served through a React frontend and FastAPI gateway.

Currently in active development. MS3 (Sentiment Analyser) is ~40% built using the legacy `sentimentAnalyser_service/` (Flask + TextBlob/VADER). All other services are being built from scratch as part of the phased implementation plan below.

---

## Architecture

| Service | Tech | Role |
|---------|------|------|
| MS1 - Gateway | FastAPI, PyJWT, SQLite | Auth (signup/login), routing, task orchestration |
| MS2 - Data Ingestor | Yahoo Finance API, PostgreSQL+TimescaleDB, Redis | Fetch/store OHLCV data, cache to Redis |
| MS3 - Sentiment | FinBERT (HuggingFace), PRAW, Celery | Reddit sentiment via FinBERT (replaces VADER) |
| MS4 - Technical | Pandas | RSI, MACD, SMA → Buy/Sell/Hold signals |
| MS5 - Frontend | React, TypeScript, Tailwind+shadcn/ui, Recharts | Dashboard, portfolio, analysis UI |
| MS6 - Forecasting | ARIMA (statsmodels), LSTM (PyTorch), Celery | Price forecasting (6m/12m/3y) |

**Communication**: Celery + Redis message broker
**Docker**: Per-service Dockerfiles + root `docker-compose.yml` orchestrator
**Data access**: MS2 caches OHLCV to Redis; other services read from Redis cache
**Error handling**: Graceful degradation (show available results, indicate failures)

### Inter-Service Flow

```
User → Frontend → Gateway (POST /analyze)
                    ↓
              Creates task_id, dispatches to Celery+Redis
                    ↓
         data-worker fetches OHLCV → caches to Redis + persists to PostgreSQL
                    ↓ (after data ready)
         Selected workers run in parallel:
           sentiment-worker → FinBERT analysis → stores result
           technical-worker → indicators from Redis cache → stores result
           forecast-worker  → ARIMA+LSTM from Redis cache → stores result
                    ↓
         Frontend polls GET /tasks/{task_id}
           → Gateway aggregates sub-task results
           → Returns partial/complete status + results
```

---

## Directory Structure

```
StonksManager/
├── docker-compose.yml              # Root orchestrator
├── .env.example
├── .github/workflows/
│   └── build.yml                   # Multi-service matrix CI
├── gateway_service/                # MS1
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py                 # FastAPI app
│       ├── config.py
│       ├── database.py             # SQLite (auth DB)
│       ├── auth/                   # signup, login, JWT
│       ├── tasks/                  # /analyze, /tasks/{id}, Celery dispatch
│       ├── portfolios/             # CRUD portfolio endpoints
│       └── middleware.py           # Rate limiting (slowapi), CORS
├── data_service/                   # MS2
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py                 # Health endpoint
│       ├── models.py               # StockMeta, StockPrice ORM
│       ├── fetcher.py              # Yahoo Finance OHLCV fetcher
│       ├── cache.py                # Redis read/write helpers
│       ├── database.py             # PostgreSQL+TimescaleDB session
│       └── worker.py               # Celery task: fetch_stock_data
├── sentiment_service/              # MS3
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py
│       ├── reddit_client.py        # Migrated from reddit_sentiment.py
│       ├── finbert_analyzer.py     # FinBERT via HuggingFace transformers
│       ├── preprocessing.py        # Migrated from sentiment_analyzer.py
│       └── worker.py               # Celery task: analyze_sentiment
├── technical_service/              # MS4
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── indicators.py           # SMA, EMA, RSI, MACD
│       ├── signals.py              # Buy/Sell/Hold logic
│       └── worker.py               # Celery task: run_technical_analysis
├── forecast_service/               # MS6
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── arima_model.py
│       ├── lstm_model.py
│       ├── ensemble.py             # Weighted average + certainty score
│       └── worker.py               # Celery task: run_forecast
├── frontend_service/               # MS5
│   ├── Dockerfile                  # Multi-stage: node build → nginx serve
│   ├── package.json
│   └── src/
│       ├── api/client.ts           # Axios + JWT interceptor
│       ├── context/AuthContext.tsx
│       ├── hooks/useTaskPolling.ts # Poll /tasks/{id} every 3s
│       ├── pages/                  # Login, Dashboard, Analysis, Portfolio
│       └── components/
└── sentimentAnalyser_service/      # LEGACY — delete after MS3 migration
```

---

## Database Schema

### Auth DB (SQLite — gateway_service)

```sql
users (id UUID PK, email UNIQUE, username UNIQUE, hashed_pw, created_at)
portfolios (id UUID PK, user_id FK→users, name, created_at)
portfolio_stocks (portfolio_id FK, symbol, PRIMARY KEY (portfolio_id, symbol))
```

### Market DB (PostgreSQL + TimescaleDB — data_service)

```sql
stock_meta (symbol PK, name, sector, currency, last_fetched)
stock_prices (symbol, date, open, high, low, close, volume) -- hypertable on date
analysis_results (id PK, task_id, symbol, analysis_type, result_json JSONB, created_at)
```

---

## API Endpoints (Gateway — MS1)

```
POST /auth/signup        → { access_token }
POST /auth/login         → { access_token }
GET  /auth/me            → user profile

POST /analyze            → { task_id }
GET  /tasks/{task_id}    → { status, results }

GET  /stock/{symbol}/price    → current price + recent OHLCV
GET  /stock/{symbol}/history  → historical OHLCV

CRUD /portfolios              → user portfolio management
GET  /health                  → gateway health
```

`POST /analyze` body: `{ symbol, analyses: ["sentiment","technical","forecast"], forecast_timeframe?: "6m"|"12m"|"3y" }`

---

## Build & Run

```bash
# Start all services (from repo root)
docker-compose up

# Start specific services only
docker-compose up redis postgres data-worker

# Legacy sentiment analyser (pre-migration, from sentimentAnalyser_service/)
FLASK_APP=src/app.py PYTHONPATH=src flask run --host=0.0.0.0
```

**CI:** GitHub Actions (`.github/workflows/build.yml`) — matrix build across all services on push/PR to main.

---

## Environment Variables

All variables should be set in a `.env` file at the repo root (not committed). See `.env.example`.

| Variable | Used By | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | MS2, docker-compose | PostgreSQL database name |
| `POSTGRES_USER` | MS2, docker-compose | PostgreSQL user |
| `POSTGRES_PASSWORD` | MS2, docker-compose | PostgreSQL password |
| `REDIS_URL` | MS1–MS4, MS6 | Redis connection string |
| `DATABASE_URL` | MS2 | Full PostgreSQL connection string |
| `JWT_SECRET_KEY` | MS1 | Secret for signing JWTs |
| `REDDIT_CLIENT_ID` | MS3 | Reddit API credentials |
| `REDDIT_CLIENT_SECRET` | MS3 | Reddit API credentials |
| `REDDIT_USER_AGENT` | MS3 | Reddit API credentials |

---

## Implementation Phases

### Phase 1: Infrastructure + Data Pipeline (MS2) ✅
1. Create root `docker-compose.yml` with Redis + PostgreSQL (timescale/timescaledb:latest-pg16)
2. Build `data_service/`: SQLAlchemy models, Yahoo Finance fetcher, Redis cache helpers, Celery worker
3. Create TimescaleDB hypertable for `stock_prices`
4. **Verify**: `docker-compose up redis postgres data-worker`, dispatch `fetch_stock_data("AAPL")`, confirm data in DB + Redis

### Phase 2: API Gateway (MS1)
1. Build `gateway_service/`: FastAPI app, SQLite auth DB, JWT auth (signup/login), Celery task dispatch, portfolio CRUD, rate limiting via slowapi
2. Wire `/analyze` to create task IDs and dispatch to Celery queues; `/tasks/{id}` to poll results
3. **Verify**: Sign up via curl, use JWT to call `/analyze`, get `task_id` back

### Phase 3: Sentiment Service Refactor (MS3)
1. Create `sentiment_service/` — migrate PRAW code from existing `reddit_sentiment.py`, replace TextBlob/VADER with FinBERT (`ProsusAI/finbert`)
2. Extract preprocessing utils from existing `sentiment_analyzer.py`
3. Pre-download FinBERT model in Dockerfile
4. **Verify**: Dispatch sentiment task, verify FinBERT labels (positive/negative/neutral with confidence)

### Phase 4: Technical Analysis Service (MS4)
1. Build `technical_service/`: SMA, EMA, RSI, MACD in pure Pandas
2. Signal logic: RSI < 30 + MACD positive = BUY, RSI > 70 + MACD negative = SELL, else HOLD
3. Reads OHLCV from Redis cache (populated by MS2)
4. **Verify**: Ensure MS2 cached data, dispatch technical analysis, verify indicators + signal

### Phase 5: Forecasting Service (MS6)
1. Build `forecast_service/`: ARIMA via statsmodels, LSTM via PyTorch
2. Ensemble: weighted average (0.4 ARIMA + 0.6 LSTM), certainty = model agreement
3. Timeframes: 6m=126 days, 12m=252 days, 3y=756 days
4. Celery worker with `--concurrency=1` (memory-heavy)
5. **Verify**: Dispatch forecast for AAPL 6m, verify prediction points + certainty score

### Phase 6: Frontend (MS5)
1. Scaffold with Vite (React + TypeScript), install Tailwind + shadcn/ui + Recharts
2. Build pages: Login, Dashboard, Analysis, Portfolio
3. Polling via `useTaskPolling` hook (every 3s on `/tasks/{id}`)
4. Progressive display: cards appear as each analysis completes; failed analyses show error state
5. Dockerfile: multi-stage (node build → nginx serve), nginx proxies `/api/*` to gateway
6. **Verify**: Full flow — sign up, search AAPL, select analyses, see results populate

### Phase 7: Integration + Cleanup
1. Delete `sentimentAnalyser_service/` entirely
2. Update `.github/workflows/build.yml` to matrix build all services + run tests
3. Create `.env.example` with all required variables
4. Update README

---

## Testing Strategy

| Service | Framework | Key Focus |
|---------|-----------|-----------|
| MS1 Gateway | pytest + httpx TestClient | Auth flow, task dispatch, rate limits |
| MS2 Data | pytest + fakeredis | Fetcher output shape, cache round-trip |
| MS3 Sentiment | pytest | FinBERT output shape, Reddit client parsing |
| MS4 Technical | pytest | Indicator math (known sequences), signal logic |
| MS5 Frontend | Jest + React Testing Library | Component rendering, polling, auth flow |
| MS6 Forecast | pytest | ARIMA/LSTM output length, ensemble agreement |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FinBERT Docker image ~1.5GB | Multi-stage build, pre-download model during build, aggressive `.dockerignore` |
| LSTM training slow per request | For 6m use ARIMA only; cache model weights in Redis (24h TTL) per symbol |
| Reddit API rate limits | Cache Reddit results in Redis (30min TTL per symbol), PRAW has built-in rate limiting |
| Celery task correlation (multiple sub-tasks per task_id) | Store sub-task IDs in Redis under parent task_id key; polling endpoint checks each individually |
| Yahoo Finance rate limiting | Single API call per symbol (OHLCV + meta combined), retry with 30s delay on 429 |
