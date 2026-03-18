# Stonkfolio

A self-hosted portfolio tracker that imports transactions from multiple brokers and provides performance analytics, allocation breakdowns, interactive charts, and AI-powered stock recommendations.

## Features

- **Multi-broker import** — CSV import for DeGiro, Trade Republic, Interactive Brokers, and Bitpanda
- **Holdings dashboard** — Real-time portfolio value, cost basis, and gain/loss overview
- **Performance charts** — Historical portfolio value with configurable time periods (1W to ALL)
- **Allocation breakdown** — Pie charts grouped by sector, country, or asset type
- **Interactive instrument charts** — Candlestick/line charts with volume overlay, SMA 20/50 indicators, and RSI 14 (powered by TradingView Lightweight Charts)
- **Stock detail** — Per-instrument view with current price, latest news, and technical analysis
- **AI recommendations** — Buy/Hold/Sell signals based on SMA crossovers and momentum indicators
- **Multi-user** — JWT authentication with isolated portfolios per user
- **Dark/light theme** — System-aware theme toggle with manual override
- **Configurable settings** — Base currency, display preferences, default broker for imports

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 5, Django REST Framework, SimpleJWT |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS v4, shadcn/ui |
| Portfolio charts | Recharts |
| Instrument charts | TradingView Lightweight Charts v4 |
| Server state | TanStack Query v5 (React Query) |
| Market data | yfinance |
| Database | PostgreSQL 16 |
| Infrastructure | Docker Compose |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) Node.js 22+ and Python 3.13+ for local development

### 1. Clone and configure

```bash
git clone https://github.com/your-username/stonkfolio.git
cd stonkfolio
cp .env.example .env
# Edit .env — change DJANGO_SECRET_KEY and POSTGRES_PASSWORD
```

### 2. Start with Docker Compose

```bash
docker compose up --build
```

This starts:

- **PostgreSQL** on port 5432
- **Django backend** on [http://localhost:8000](http://localhost:8000)
- **Next.js frontend** on [http://localhost:3000](http://localhost:3000)

### 3. Create the database tables

```bash
docker compose exec backend python manage.py migrate
```

### 4. Open the app

Navigate to [http://localhost:3000](http://localhost:3000), register an account, and start importing transactions.

### Production Deployment

Use the production override for secure defaults (gunicorn, localhost-only ports, DEBUG off):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

Make sure to set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and `CORS_ALLOWED_ORIGINS` in your `.env`.

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Running Tests

### Backend

```bash
cd backend
python -m pytest -v                              # all tests (91 tests)
python -m pytest apps/brokers/tests/ -v          # specific app
python -m pytest path/test.py::Class::method -v  # single test
```

Tests use SQLite in-memory (via `config/test_settings.py`), so no PostgreSQL needed.

### Frontend

```bash
cd frontend
npm test
```

## Linting

```bash
# Backend
cd backend
python -m ruff check .
python -m ruff format --check .

# Frontend
cd frontend
npx eslint src/
```

## Importing Transactions

1. Go to the **Import** page
2. Select your broker (DeGiro, Trade Republic, Interactive Brokers, or Bitpanda)
3. Upload your CSV export
4. Review the parsed transactions in the preview table
5. Confirm to import

Duplicate transactions are automatically skipped based on a hash of the transaction data.

### CSV Formats

| Broker | Export source |
|--------|-------------|
| DeGiro | Account → Transactions → Export |
| Trade Republic | Activity → Export as CSV |
| Interactive Brokers | Flex Queries → Trade Confirmation |
| Bitpanda | Transaction history → Download CSV |

## Environment Variables

| Variable | Description | Default |
|----------|------------|---------|
| `POSTGRES_DB` | Database name | `stonkfolio` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `changeme` |
| `DJANGO_SECRET_KEY` | Django secret key | *(required)* |
| `DJANGO_DEBUG` | Debug mode | `False` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts (prod) | `localhost` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated CORS origins (prod) | `http://localhost:3000` |

## API Endpoints

| Endpoint | Description |
|----------|------------|
| `POST /api/auth/register/` | Register new user (rate-limited: 5/hour) |
| `POST /api/auth/login/` | Obtain JWT tokens |
| `POST /api/auth/token/refresh/` | Refresh access token |
| `GET /api/portfolios/` | List user portfolios |
| `GET /api/portfolios/:id/holdings/` | Portfolio holdings |
| `GET /api/portfolios/:id/summary/` | Portfolio value summary |
| `GET /api/portfolios/:id/performance/` | Historical performance series |
| `GET /api/portfolios/:id/allocation/` | Allocation breakdown |
| `POST /api/portfolios/:id/import/csv/` | Upload CSV for preview |
| `POST /api/portfolios/:id/import/csv/confirm/` | Confirm import |
| `GET /api/instruments/:id/` | Instrument detail + news |
| `GET /api/instruments/:id/analysis/` | AI recommendation |
| `GET /api/instruments/:id/chart/?period=6M` | OHLCV chart data + indicators |

## License

MIT
