# Portfolio Tracker — Design Spec

## Purpose

A multi-user portfolio tracker that imports stock data from brokers (DeGiro first, others later) and provides holdings overview, performance charts, allocation breakdowns, and transaction history.

## Stack

- **Backend:** Django + Django REST Framework, Python 3.12+
- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS
- **Database:** PostgreSQL
- **Deployment:** Docker Compose (three containers: backend, frontend, db)

## Backend Architecture

```
backend/
  config/           # Django project settings, urls, wsgi
  apps/
    users/          # User model, auth (JWT via simplejwt)
    portfolios/     # Portfolio, Holding, Transaction models
    instruments/    # Instrument model, ISIN-to-ticker mapping
    brokers/        # Broker abstraction + importer implementations
    market_data/    # Price fetching service
```

### Instrument Model

A normalized `Instrument` entity is the canonical source of security metadata:

```python
class Instrument:
    isin: str              # primary identifier (unique)
    ticker: str | None     # yfinance-compatible ticker (resolved via lookup)
    name: str
    currency: str
    sector: str | None     # fetched from yfinance on first resolution
    country: str | None    # geography for allocation
    asset_type: str        # STOCK, ETF, BOND, etc.
```

**ISIN-to-ticker mapping:** DeGiro exports use ISINs. On first import, the system attempts to resolve each ISIN to a yfinance ticker using the `yfinance` search API. The resolved mapping is stored on the `Instrument` and cached. Unresolved instruments are flagged for manual mapping via the UI.

Holdings and Transactions reference `Instrument` via foreign key instead of storing raw ticker strings.

### Broker Abstraction

A `BrokerImporter` base class defines the interface for importing transactions from any broker:

```python
class BrokerImporter(ABC):
    @abstractmethod
    def import_transactions(self, source) -> list[TransactionData]: ...
```

Returns a list of `TransactionData` (a plain dataclass, not ORM objects). The import service handles deduplication, instrument resolution, and persistence.

DeGiro gets two implementations:
- `DegiroCsvImporter` — parses uploaded CSV files
- `DegiroApiImporter` — pulls via `degiro-connector` library

Adding a new broker (e.g., Trade Republic) means implementing a new `BrokerImporter` subclass. Nothing else changes.

**Transaction types:** `BUY`, `SELL`, `DIVIDEND`, `FEE`, `FX`. Non-standard rows in CSV exports (e.g., currency conversions, standalone fees) are mapped to `FEE` or `FX` types. Unknown rows are skipped with a warning surfaced to the user.

**Deduplication:** Each transaction gets a `broker_reference` field (a hash of broker + date + ISIN + quantity + price). Re-importing the same CSV skips already-imported transactions. Imports are atomic — if parsing fails partway, nothing is committed.

### Market Data Service

A `PriceProvider` interface abstracts price fetching:

```python
class PriceProvider(ABC):
    @abstractmethod
    def get_current_price(self, ticker: str) -> PriceResult: ...

    @abstractmethod
    def get_historical_prices(self, ticker: str, start: date, end: date) -> list[PricePoint]: ...
```

v1 implementation: `YFinancePriceProvider` (fetches on demand via `yfinance`). Both current and historical prices are available through `yfinance`.

Future: swap to a `CachedPriceProvider` that reads from a background-synced database table, implementing the same interface.

### Auth

JWT-based via `djangorestframework-simplejwt`. Standard register/login/refresh flow.

## Data Model

```
User (Django built-in, extended with base_currency field, default EUR)
  └── Portfolio (name, created_at)
        ├── Holding (instrument_fk, quantity, avg_buy_price)
        ├── Transaction (instrument_fk, type[BUY/SELL/DIVIDEND/FEE/FX], quantity, price,
        │                fee, date, broker_source, broker_reference)
        └── BrokerConnection (broker_type, credentials_encrypted, last_sync)

Instrument (isin, ticker, name, currency, sector, country, asset_type)

MarketData
  └── PriceCache (instrument_fk, price, fetched_at)
```

**Key decisions:**
- A user can have multiple portfolios (e.g., "Long term", "Speculative").
- Transactions are the source of truth — holdings are recalculated from transactions on each import. The `Holding` model is a materialized cache for fast reads.
- `broker_reference` on each transaction enables deduplication across re-imports.
- `PriceCache` is TTL-based (5 min), lays groundwork for future background sync.
- `BrokerConnection` belongs to the user (not a specific portfolio). The import endpoint is portfolio-scoped — it uses the user's broker connection to import into the selected portfolio.
- **Currency:** All monetary values are displayed in the user's `base_currency`. Conversion uses exchange rates from `yfinance`. v1 does not store historical exchange rates — it converts at the current rate.
- **Pagination:** All list endpoints use cursor-based pagination (DRF's `CursorPagination`), default page size 50.

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login, returns JWT |
| POST | `/api/auth/refresh/` | Refresh JWT token |

### User
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/PATCH | `/api/user/me/` | Get/update profile (base_currency, password) |

### Portfolios
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/portfolios/` | List/create portfolios |
| GET/PUT/DELETE | `/api/portfolios/:id/` | Portfolio CRUD |
| GET | `/api/portfolios/:id/holdings/` | List of holdings with current prices and gain/loss |
| GET | `/api/portfolios/:id/summary/` | Aggregate totals: value, gain/loss, return % |
| GET | `/api/portfolios/:id/performance/?period=1M` | Time series, accepts `period` param (1W/1M/3M/6M/1Y/ALL) |
| GET | `/api/portfolios/:id/allocation/?group_by=sector` | Grouped breakdown, accepts `group_by` param (sector/country/asset_type) |

### Transactions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/portfolios/:id/transactions/` | List/create (filterable, sortable, paginated) |
| GET/PUT/DELETE | `/api/transactions/:id/` | Transaction CRUD |

### Import
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/portfolios/:id/import/csv/` | Upload CSV, returns preview |
| POST | `/api/portfolios/:id/import/csv/confirm/` | Confirm previewed import |
| POST | `/api/portfolios/:id/import/sync/` | Trigger API sync via broker connection |

### Broker Connections
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/broker-connections/` | List/create connections (user-scoped) |
| DELETE | `/api/broker-connections/:id/` | Remove connection |

### Market Data
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/prices/:ticker/` | Current price (cached or fresh) |

## Frontend Architecture

```
frontend/
  src/
    app/              # Next.js App Router pages
      (auth)/         # Login, register
      dashboard/      # Holdings overview (main page)
      performance/    # Portfolio value over time charts
      allocation/     # Sector/geography/asset type breakdowns
      transactions/   # Transaction history table
      import/         # CSV upload + broker API connection
      settings/       # User profile, base currency
    components/       # Shared UI components (charts, tables, layout)
    lib/
      api/            # Typed API client wrapping fetch
    types/            # Shared TypeScript types
```

**Libraries:**
- **UI:** shadcn/ui (Tailwind-based components)
- **Charts:** Recharts
- **Server state:** TanStack Query (React Query)
- **API client:** Thin typed wrapper around fetch

## Frontend Pages — v1

### Dashboard (Holdings Overview)
- Table: ticker, name, quantity, avg buy price, current price, total value, gain/loss (absolute + %)
- Portfolio total value and total gain/loss at the top
- Portfolio selector dropdown

### Performance
- Line chart: portfolio value over time
- Period selector: 1W, 1M, 3M, 6M, 1Y, ALL
- Return % displayed

### Allocation
- Pie chart by sector
- Pie chart by geography
- Treemap by asset type
- Toggle between views

### Transactions
- Searchable, filterable, sortable table with pagination
- Columns: date, ticker, type (buy/sell/dividend/fee/fx), quantity, price, fee, total, broker source
- Filters: date range, type, ticker

### Import
- CSV file upload with drag-and-drop
- Broker selector (DeGiro initially)
- Preview of parsed transactions before confirming import
- Unresolved instruments flagged with manual ticker input
- Broker API connection setup (credentials form)
- Manual sync trigger

### Settings
- Base currency selector
- Change password

## Docker Compose Setup

Three services:
- `db` — PostgreSQL 16
- `backend` — Django app, exposes port 8000
- `frontend` — Next.js app, exposes port 3000

Backend connects to db. Frontend calls backend API. Environment variables for config (DB credentials, JWT secret, etc).
