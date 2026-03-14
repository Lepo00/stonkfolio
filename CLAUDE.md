# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
docker compose up              # start all services (db, backend :8000, frontend :3000)
docker compose up -d db        # start just PostgreSQL

# Production (gunicorn, ports bound to localhost, DEBUG=False)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up

# Backend
cd backend
python -m pytest                                           # run all tests (91 tests, uses SQLite)
python -m pytest path/to/test.py::TestClass::test_method -v  # run single test
python -m ruff check .                                     # lint
python manage.py runserver                                 # run outside Docker (needs db)

# Frontend
cd frontend
npm run dev       # dev server
npm run build     # production build
npm test          # run tests (jest)
npx eslint src/   # lint
```

## Architecture

- **Backend**: Django 5 + DRF, JWT auth (simplejwt), PostgreSQL 16, market data via yfinance
- **Frontend**: Next.js 16 App Router, TypeScript (strict), React 19, shadcn/ui, TanStack Query v5, Tailwind v4
- **Charts**: Recharts for portfolio-level (allocation pies, performance line); TradingView Lightweight Charts v4 for instrument-level (OHLC candlestick/line, volume overlay, SMA/RSI indicators)
- **Infra**: docker-compose with `db`, `backend`, `frontend` services. Config via `.env` + python-decouple. Production override in `docker-compose.prod.yml`

## App Structure (backend)

| App | Purpose |
|-----|---------|
| `apps.users` | Custom User model, JWT registration/login, registration rate-limited (5/hour) |
| `apps.portfolios` | Portfolio CRUD, transaction log, holdings, summary/performance/allocation analytics |
| `apps.brokers` | Broker import (CSV + API) for DeGiro, Trade Republic, Interactive Brokers, Bitpanda. CSV values sanitized against injection. |
| `apps.instruments` | Instrument detail, AI analysis, interactive chart endpoint (OHLC + indicators) |
| `apps.market_data` | Price fetching (PriceProvider ABC), historical data cache, OHLCV data, SMA/RSI calculation (`indicators.py`) |

Frontend uses `@/*` path alias mapping to `src/*`. Route groups: `(app)` for authenticated, `(auth)` for login/register.

## Key Patterns

- **Broker importers** extend `BrokerImporter` ABC (`apps/brokers/importers/base.py`). Each returns `list[TransactionData]` from `import_transactions(source)`. TransactionTypes: BUY, SELL, DIVIDEND, FEE, FX.
- **Price providers** extend `PriceProvider` ABC (`apps/market_data/providers/base.py`). Currently only `yfinance_provider.py`. `get_ohlcv()` returns `pd.DataFrame`.
- **Holdings are derived from transactions** with a materialized cache — not stored as independent records.
- **CursorPagination** is the default pagination. Every viewset must define an `ordering` field or queries will fail.
- **Tests** use `config.test_settings` which swaps PostgreSQL for in-memory SQLite. No Docker needed for tests.
- **Chart data** is fetched on-the-fly from yfinance (no DB caching). Indicators (SMA 20/50, RSI 14) are calculated server-side. Intraday data uses Unix timestamps; daily data uses YYYY-MM-DD strings.
- **Token refresh**: The frontend API client automatically attempts token refresh on 401 before redirecting to login.

## Security Notes

- Ports are bound to `127.0.0.1` in docker-compose (not exposed to 0.0.0.0)
- Production mode (`DJANGO_DEBUG=False`) enables HSTS, SSL redirect, secure cookies, CORS allowlist
- Password minimum length is 10 characters (must match between serializer and Django validator)
- Registration is throttled at 5 requests/hour per IP

## Important

NEVER include `Co-Authored-By` lines in git commit messages when working on this project.
