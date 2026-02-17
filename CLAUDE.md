# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## General Rules

- Always confirm with the user before writing code, editing files, or running terminal commands.
- When implementing changes, explain the reasoning behind each decision — why this approach, why this tool/library, and how it fits into the overall architecture. Treat this as a learning walkthrough, not just code delivery.

## Project Overview

StonksManager is a stock sentiment analysis tool that combines Reddit post sentiment with stock price data. It provides both a Flask web interface and a CLI tool.

## Build & Run Commands

All commands run from `sentimentAnalyser_service/`.

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Docker
docker-compose up          # serves on http://localhost:8080

# Run Flask locally (requires .env with Reddit API credentials)
FLASK_APP=src/app.py PYTHONPATH=src flask run --host=0.0.0.0

# Run CLI tool
python stock_sentiment.py
```

**CI:** GitHub Actions (`.github/workflows/build.yml`) validates Docker builds on push/PR to main. No test suite or linter is configured.

## Architecture

The project is a single service (`sentimentAnalyser_service/`) with this structure:

- **`src/app.py`** — Flask app entry point. Routes: `GET /` (web UI), `POST /analyze` (accepts `stock_symbol`, returns JSON with sentiment + price data)
- **`src/reddit_sentiment.py`** — `RedditSentimentAnalyzer` class. Uses PRAW to fetch posts from r/stocks, r/investing, r/wallstreetbets and scores sentiment via TextBlob
- **`src/stock_data.py`** — `StockDataFetcher` class. Fetches current stock prices via yfinance with retry logic
- **`src/models/sentiment_analyzer.py`** — `EnhancedSentimentAnalyzer` using VADER + scikit-learn features (text length, punctuation counts)
- **`src/visualization/plotter.py`** — `SentimentPlotter` for matplotlib charts with 7-day moving average trends
- **`stock_sentiment.py`** — Standalone CLI analyzer combining Reddit sentiment + yfinance predictions

**Data flow (web):** User submits stock symbol → Flask `/analyze` → RedditSentimentAnalyzer fetches & scores posts → StockDataFetcher gets price → JSON response → frontend renders results.

## Environment Variables

Required in `.env` (not committed):
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` — Reddit API credentials

Set by Docker/Flask config:
- `FLASK_APP=src/app.py`, `PYTHONPATH=/app/src`, `PYTHONUNBUFFERED=1`

