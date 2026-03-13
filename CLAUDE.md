# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
docker compose up              # start all services (db, backend :8000, frontend :3000)
docker compose up -d db        # start just PostgreSQL

# Backend
cd backend
python -m pytest                                           # run all tests
python -m pytest path/to/test.py::TestClass::test_method -v  # run single test
python manage.py runserver                                 # run outside Docker (needs db)

# Frontend
cd frontend
npm run dev       # dev server
npm run build     # production build
npm test          # run tests
npx eslint .      # lint
```

## Architecture

- **Backend**: Django 5 + DRF, JWT auth (simplejwt), PostgreSQL 16, market data via yfinance
- **Frontend**: Next.js 16 App Router, TypeScript (strict), React 19, shadcn/ui, TanStack Query v5, Recharts, Tailwind v4
- **Infra**: docker-compose with `db`, `backend`, `frontend` services. Config via `.env` + python-decouple

## App Structure (backend)

| App | Purpose |
|-----|---------|
| `apps.users` | Custom User model, JWT registration/login |
| `apps.portfolios` | Portfolio CRUD, transaction log, holdings, analytics |
| `apps.brokers` | Broker import (CSV + API) for DeGiro, Trade Republic, Interactive Brokers, Bitpanda |
| `apps.instruments` | Instrument detail and analysis |
| `apps.market_data` | Price fetching, historical data cache, currency conversion |

Frontend uses `@/*` path alias mapping to `src/*`. Route groups: `(app)` for authenticated, `(auth)` for login/register.

## Key Patterns

- **Broker importers** extend `BrokerImporter` ABC (`apps/brokers/importers/base.py`). Each returns `list[TransactionData]` from `import_transactions(source)`. TransactionTypes: BUY, SELL, DIVIDEND, FEE, FX.
- **Price providers** extend `PriceProvider` ABC (`apps/market_data/providers/base.py`). Currently only `yfinance_provider.py`.
- **Holdings are derived from transactions** with a materialized cache — not stored as independent records.
- **CursorPagination** is the default pagination. Every viewset must define an `ordering` field or queries will fail.
- **Tests** use `config.test_settings` which swaps PostgreSQL for in-memory SQLite. No Docker needed for tests.

## Important

NEVER include `Co-Authored-By` lines in git commit messages when working on this project.
