# Stonkfolio Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Stonkfolio — a multi-user portfolio tracker with Django+DRF backend, Next.js frontend, PostgreSQL database, deployed via Docker Compose. Imports from DeGiro (CSV + API), shows holdings, performance, allocation, and transactions.

**Architecture:** Three-container Docker Compose (db, backend, frontend). Django apps: users, instruments, portfolios, brokers, market_data. Next.js App Router with shadcn/ui, Recharts, TanStack Query. Broker import via abstract `BrokerImporter`, market data via abstract `PriceProvider`.

**Tech Stack:** Python 3.12, Django 5, DRF, simplejwt, yfinance, degiro-connector | Node 20, Next.js 14, TypeScript, Tailwind, shadcn/ui, Recharts, TanStack Query | PostgreSQL 16, Docker Compose

**Spec:** `docs/superpowers/specs/2026-03-13-portfolio-tracker-design.md`

**Note:** All `git commit` commands in this plan omit Co-Authored-By lines.

---

## Chunk 1: Project Scaffolding & Docker

### Task 1: Docker Compose + PostgreSQL

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Create .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
db.sqlite3

# Node
node_modules/
.next/
frontend/.next/

# Environment
.env
.env.local

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
```

- [ ] **Step 2: Create .env.example**

```env
POSTGRES_DB=stonkfolio
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changeme
DJANGO_SECRET_KEY=changeme
DJANGO_DEBUG=True
DATABASE_URL=postgres://postgres:changeme@db:5432/stonkfolio
```

- [ ] **Step 3: Create docker-compose.yml**

```yaml
services:
  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    env_file: .env
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    command: npm run dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    env_file: .env
    depends_on:
      - backend

volumes:
  postgres_data:
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore .env.example docker-compose.yml
git commit -m "chore: add Docker Compose config with PostgreSQL"
```

### Task 2: Django Project Scaffolding

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/requirements.txt`
- Create: `backend/manage.py`
- Create: `backend/config/__init__.py`
- Create: `backend/config/settings.py`
- Create: `backend/config/urls.py`
- Create: `backend/config/wsgi.py`

- [ ] **Step 1: Create backend/Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
```

- [ ] **Step 2: Create backend/requirements.txt**

```
django>=5.0,<6.0
djangorestframework>=3.15,<4.0
djangorestframework-simplejwt>=5.3,<6.0
django-filter>=24.0
django-cors-headers>=4.3,<5.0
psycopg[binary]>=3.1,<4.0
yfinance>=0.2,<1.0
degiro-connector>=2.0,<3.0
python-decouple>=3.8,<4.0
```

- [ ] **Step 3: Create Django project structure**

Create `backend/manage.py` (standard Django manage.py with `config.settings`).

Create `backend/config/settings.py`:
```python
from pathlib import Path
from datetime import timedelta
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY", default="insecure-dev-key")
DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "django_filters",
    "corsheaders",
    # Local
    "apps.users",
    "apps.instruments",
    "apps.portfolios",
    "apps.brokers",
    "apps.market_data",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "users.User"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="stonkfolio"),
        "USER": config("POSTGRES_USER", default="postgres"),
        "PASSWORD": config("POSTGRES_PASSWORD", default="changeme"),
        "HOST": config("DATABASE_HOST", default="db"),
        "PORT": config("DATABASE_PORT", default="5432"),
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

CORS_ALLOW_ALL_ORIGINS = DEBUG

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

Create `backend/config/urls.py`:
```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.urls")),
]
```

Create `backend/config/wsgi.py` (standard, pointing to `config.settings`).

Create `backend/config/__init__.py` (empty).

Create `backend/apps/__init__.py` (empty).

Create `backend/apps/urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    path("auth/", include("apps.users.urls")),
    path("user/", include("apps.users.profile_urls")),
    path("", include("apps.portfolios.urls")),
    path("", include("apps.brokers.urls")),
    path("", include("apps.market_data.urls")),
]
```

- [ ] **Step 4: Create empty Django apps**

Create the following empty app directories, each with `__init__.py`, `models.py`, `views.py`, `urls.py`, `serializers.py`, `admin.py`, `apps.py`:
- `backend/apps/users/`
- `backend/apps/instruments/`
- `backend/apps/portfolios/`
- `backend/apps/brokers/`
- `backend/apps/market_data/`

Each `apps.py` should set `name = "apps.<app_name>"`.

**Important:** Each empty `urls.py` must contain `urlpatterns = []` so Django can import them without error.

- [ ] **Step 5: Create backend/pytest.ini**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py *_tests.py
```

Also add `pytest` and `pytest-django` to `backend/requirements.txt`.

- [ ] **Step 6: Verify Docker build**

```bash
cp .env.example .env
docker compose build backend
```

Expected: builds successfully.

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "chore: scaffold Django project with all apps and pytest config"
```

### Task 3: Next.js Project Scaffolding

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/next.config.js`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx`

- [ ] **Step 1: Scaffold Next.js project**

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --no-git
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install @tanstack/react-query recharts
npx shadcn@latest init -d
```

- [ ] **Step 3: Create frontend/Dockerfile**

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

EXPOSE 3000
```

- [ ] **Step 4: Create API client base**

Create `frontend/src/lib/api/client.ts`:
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
};

export async function apiClient<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const token = typeof window !== "undefined"
    ? localStorage.getItem("access_token")
    : null;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new ApiError(res.status, error);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export class ApiError extends Error {
  constructor(public status: number, public data: unknown) {
    super(`API error ${status}`);
  }
}
```

- [ ] **Step 5: Set up TanStack Query provider**

Create `frontend/src/lib/providers.tsx`:
```typescript
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

Update `frontend/src/app/layout.tsx` to wrap children with `<Providers>`.

- [ ] **Step 6: Verify Docker build**

```bash
docker compose build frontend
```

Expected: builds successfully.

- [ ] **Step 7: Verify full stack starts**

```bash
docker compose up -d
```

Expected: all three containers healthy. `http://localhost:3000` shows Next.js page. `http://localhost:8000/admin/` shows Django (will error on missing migrations, that's fine).

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "chore: scaffold Next.js project with TanStack Query and API client"
```

---

## Chunk 2: Backend Models & Auth

### Task 4: User Model + Auth Endpoints

**Files:**
- Create: `backend/apps/users/models.py`
- Create: `backend/apps/users/serializers.py`
- Create: `backend/apps/users/views.py`
- Create: `backend/apps/users/urls.py`
- Create: `backend/apps/users/profile_urls.py`
- Create: `backend/apps/users/tests/__init__.py`
- Create: `backend/apps/users/tests/test_auth.py`

- [ ] **Step 1: Write User model**

```python
# backend/apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    base_currency = models.CharField(max_length=3, default="EUR")
```

- [ ] **Step 2: Write failing tests for auth**

```python
# backend/apps/users/tests/test_auth.py
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

@pytest.mark.django_db
class TestAuth:
    def setup_method(self):
        self.client = APIClient()

    def test_register_creates_user(self):
        resp = self.client.post(reverse("register"), {
            "username": "testuser",
            "password": "securepass123",
            "email": "test@example.com",
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert "id" in resp.data

    def test_login_returns_tokens(self):
        from apps.users.models import User
        User.objects.create_user(username="testuser", password="securepass123")
        resp = self.client.post(reverse("token_obtain_pair"), {
            "username": "testuser",
            "password": "securepass123",
        })
        assert resp.status_code == status.HTTP_200_OK
        assert "access" in resp.data
        assert "refresh" in resp.data

    def test_me_returns_profile(self):
        from apps.users.models import User
        user = User.objects.create_user(username="testuser", password="securepass123")
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse("user_me"))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["base_currency"] == "EUR"

    def test_me_update_currency(self):
        from apps.users.models import User
        user = User.objects.create_user(username="testuser", password="securepass123")
        self.client.force_authenticate(user=user)
        resp = self.client.patch(reverse("user_me"), {"base_currency": "USD"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["base_currency"] == "USD"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && python -m pytest apps/users/tests/test_auth.py -v
```

Expected: FAIL (views/urls not implemented yet).

- [ ] **Step 4: Implement serializers, views, urls**

`backend/apps/users/serializers.py`:
```python
from rest_framework import serializers
from .models import User

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "base_currency"]
        read_only_fields = ["id", "username", "email"]
```

`backend/apps/users/views.py`:
```python
from rest_framework import generics, permissions
from .models import User
from .serializers import RegisterSerializer, UserSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class UserMeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
```

`backend/apps/users/urls.py`:
```python
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
```

`backend/apps/users/profile_urls.py`:
```python
from django.urls import path
from .views import UserMeView

urlpatterns = [
    path("me/", UserMeView.as_view(), name="user_me"),
]
```

- [ ] **Step 5: Run migrations and tests**

```bash
cd backend && python manage.py makemigrations && python manage.py migrate
python -m pytest apps/users/tests/test_auth.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/users/
git commit -m "feat: add User model with auth endpoints (register, login, refresh, me)"
```

### Task 5: Instrument Model

**Files:**
- Create: `backend/apps/instruments/models.py`
- Create: `backend/apps/instruments/serializers.py`
- Create: `backend/apps/instruments/admin.py`
- Create: `backend/apps/instruments/tests/__init__.py`
- Create: `backend/apps/instruments/tests/test_models.py`

- [ ] **Step 1: Write failing test**

```python
# backend/apps/instruments/tests/test_models.py
import pytest
from apps.instruments.models import Instrument

@pytest.mark.django_db
class TestInstrument:
    def test_create_instrument(self):
        inst = Instrument.objects.create(
            isin="IE00B4L5Y983",
            ticker="IWDA.AS",
            name="iShares Core MSCI World",
            currency="EUR",
            sector="Diversified",
            country="IE",
            asset_type="ETF",
        )
        assert inst.isin == "IE00B4L5Y983"
        assert str(inst) == "IWDA.AS - iShares Core MSCI World"

    def test_isin_unique(self):
        Instrument.objects.create(isin="IE00B4L5Y983", name="Test", currency="EUR", asset_type="ETF")
        with pytest.raises(Exception):
            Instrument.objects.create(isin="IE00B4L5Y983", name="Dupe", currency="EUR", asset_type="ETF")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest apps/instruments/tests/ -v
```

Expected: FAIL.

- [ ] **Step 3: Implement Instrument model**

```python
# backend/apps/instruments/models.py
from django.db import models

class AssetType(models.TextChoices):
    STOCK = "STOCK"
    ETF = "ETF"
    BOND = "BOND"
    FUND = "FUND"
    OTHER = "OTHER"

class Instrument(models.Model):
    isin = models.CharField(max_length=12, unique=True)
    ticker = models.CharField(max_length=20, blank=True, null=True)
    name = models.CharField(max_length=255)
    currency = models.CharField(max_length=3)
    sector = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    asset_type = models.CharField(max_length=10, choices=AssetType.choices, default=AssetType.STOCK)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ticker or self.isin} - {self.name}"
```

```python
# backend/apps/instruments/serializers.py
from rest_framework import serializers
from .models import Instrument

class InstrumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrument
        fields = ["id", "isin", "ticker", "name", "currency", "sector", "country", "asset_type"]
```

- [ ] **Step 4: Run migrations and tests**

```bash
cd backend && python manage.py makemigrations instruments && python manage.py migrate
python -m pytest apps/instruments/tests/ -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/instruments/
git commit -m "feat: add Instrument model with ISIN, ticker, sector, country, asset_type"
```

### Task 6: Portfolio, Holding, Transaction Models

**Files:**
- Create: `backend/apps/portfolios/models.py`
- Create: `backend/apps/portfolios/serializers.py`
- Create: `backend/apps/portfolios/tests/__init__.py`
- Create: `backend/apps/portfolios/tests/test_models.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/apps/portfolios/tests/test_models.py
import pytest
from datetime import date
from decimal import Decimal
from apps.users.models import User
from apps.instruments.models import Instrument
from apps.portfolios.models import Portfolio, Transaction, TransactionType

@pytest.mark.django_db
class TestPortfolioModels:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.instrument = Instrument.objects.create(
            isin="IE00B4L5Y983", ticker="IWDA.AS", name="MSCI World",
            currency="EUR", asset_type="ETF",
        )

    def test_create_portfolio(self):
        p = Portfolio.objects.create(user=self.user, name="Main")
        assert p.name == "Main"
        assert p.user == self.user

    def test_create_transaction(self):
        p = Portfolio.objects.create(user=self.user, name="Main")
        t = Transaction.objects.create(
            portfolio=p, instrument=self.instrument,
            type=TransactionType.BUY, quantity=Decimal("10"),
            price=Decimal("75.50"), fee=Decimal("2.00"),
            date=date(2025, 1, 15), broker_source="degiro",
            broker_reference="abc123",
        )
        assert t.quantity == Decimal("10")
        assert t.type == TransactionType.BUY

    def test_broker_reference_unique_per_portfolio(self):
        p = Portfolio.objects.create(user=self.user, name="Main")
        Transaction.objects.create(
            portfolio=p, instrument=self.instrument,
            type=TransactionType.BUY, quantity=Decimal("10"),
            price=Decimal("75.50"), fee=Decimal("0"),
            date=date(2025, 1, 15), broker_source="degiro",
            broker_reference="abc123",
        )
        with pytest.raises(Exception):
            Transaction.objects.create(
                portfolio=p, instrument=self.instrument,
                type=TransactionType.BUY, quantity=Decimal("5"),
                price=Decimal("76.00"), fee=Decimal("0"),
                date=date(2025, 1, 16), broker_source="degiro",
                broker_reference="abc123",
            )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest apps/portfolios/tests/test_models.py -v
```

- [ ] **Step 3: Implement models**

```python
# backend/apps/portfolios/models.py
from django.db import models
from django.conf import settings

class TransactionType(models.TextChoices):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    FEE = "FEE"
    FX = "FX"

class Portfolio(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolios")
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "name"]

    def __str__(self):
        return f"{self.user.username}/{self.name}"

class Holding(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="holdings")
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    avg_buy_price = models.DecimalField(max_digits=18, decimal_places=6)

    class Meta:
        unique_together = ["portfolio", "instrument"]

class Transaction(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="transactions")
    instrument = models.ForeignKey("instruments.Instrument", on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=TransactionType.choices)
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    price = models.DecimalField(max_digits=18, decimal_places=6)
    fee = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    date = models.DateField()
    broker_source = models.CharField(max_length=50)
    broker_reference = models.CharField(max_length=255)

    class Meta:
        unique_together = ["portfolio", "broker_reference"]
        ordering = ["-date"]
```

- [ ] **Step 4: Run migrations and tests**

```bash
cd backend && python manage.py makemigrations portfolios && python manage.py migrate
python -m pytest apps/portfolios/tests/test_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/portfolios/
git commit -m "feat: add Portfolio, Holding, Transaction models"
```

### Task 7: PriceCache Model

**Files:**
- Create: `backend/apps/market_data/models.py`
- Create: `backend/apps/market_data/tests/__init__.py`
- Create: `backend/apps/market_data/tests/test_models.py`

- [ ] **Step 1: Write failing test**

```python
# backend/apps/market_data/tests/test_models.py
import pytest
from decimal import Decimal
from apps.instruments.models import Instrument
from apps.market_data.models import PriceCache

@pytest.mark.django_db
class TestPriceCache:
    def test_create_price_cache(self):
        inst = Instrument.objects.create(
            isin="IE00B4L5Y983", name="Test", currency="EUR", asset_type="ETF",
        )
        pc = PriceCache.objects.create(instrument=inst, price=Decimal("75.50"))
        assert pc.price == Decimal("75.50")
        assert pc.fetched_at is not None
```

- [ ] **Step 2: Implement model**

```python
# backend/apps/market_data/models.py
from django.db import models

class PriceCache(models.Model):
    instrument = models.OneToOneField("instruments.Instrument", on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=18, decimal_places=6)
    fetched_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.instrument} @ {self.price}"
```

- [ ] **Step 3: Run migrations and tests**

```bash
cd backend && python manage.py makemigrations market_data && python manage.py migrate
python -m pytest apps/market_data/tests/ -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/apps/market_data/
git commit -m "feat: add PriceCache model"
```

---

## Chunk 3: Market Data & Broker Import Services

### Task 8: PriceProvider Interface + YFinance Implementation

**Files:**
- Create: `backend/apps/market_data/providers/__init__.py`
- Create: `backend/apps/market_data/providers/base.py`
- Create: `backend/apps/market_data/providers/yfinance_provider.py`
- Create: `backend/apps/market_data/services.py`
- Create: `backend/apps/market_data/tests/test_services.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/apps/market_data/tests/test_services.py
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
from apps.instruments.models import Instrument
from apps.market_data.models import PriceCache
from apps.market_data.services import MarketDataService
from apps.market_data.providers.base import PriceResult, PricePoint

@pytest.mark.django_db
class TestMarketDataService:
    def setup_method(self):
        self.instrument = Instrument.objects.create(
            isin="IE00B4L5Y983", ticker="IWDA.AS", name="Test",
            currency="EUR", asset_type="ETF",
        )

    @patch("apps.market_data.providers.yfinance_provider.yf")
    def test_get_current_price_fetches_and_caches(self, mock_yf):
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 75.5, "currency": "EUR"}
        mock_yf.Ticker.return_value = mock_ticker

        service = MarketDataService()
        result = service.get_current_price(self.instrument)

        assert result.price == Decimal("75.5")
        assert PriceCache.objects.filter(instrument=self.instrument).exists()

    @patch("apps.market_data.providers.yfinance_provider.yf")
    def test_get_current_price_uses_cache_if_fresh(self, mock_yf):
        PriceCache.objects.create(instrument=self.instrument, price=Decimal("70.00"))

        service = MarketDataService()
        result = service.get_current_price(self.instrument)

        assert result.price == Decimal("70.00")
        mock_yf.Ticker.assert_not_called()

    @patch("apps.market_data.providers.yfinance_provider.yf")
    def test_get_historical_prices(self, mock_yf):
        import pandas as pd
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {"Close": [74.0, 75.0, 76.0]},
            index=pd.to_datetime(["2025-01-13", "2025-01-14", "2025-01-15"]),
        )
        mock_yf.Ticker.return_value = mock_ticker

        service = MarketDataService()
        prices = service.get_historical_prices(
            self.instrument, date(2025, 1, 13), date(2025, 1, 15)
        )

        assert len(prices) == 3
        assert prices[0].price == Decimal("74.0")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest apps/market_data/tests/test_services.py -v
```

- [ ] **Step 3: Implement provider base**

```python
# backend/apps/market_data/providers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

@dataclass
class PriceResult:
    price: Decimal
    currency: str

@dataclass
class PricePoint:
    date: date
    price: Decimal

class PriceProvider(ABC):
    @abstractmethod
    def get_current_price(self, ticker: str) -> PriceResult: ...

    @abstractmethod
    def get_historical_prices(self, ticker: str, start: date, end: date) -> list[PricePoint]: ...
```

- [ ] **Step 4: Implement YFinance provider**

```python
# backend/apps/market_data/providers/yfinance_provider.py
import yfinance as yf
from datetime import date
from decimal import Decimal
from .base import PriceProvider, PriceResult, PricePoint

class YFinancePriceProvider(PriceProvider):
    def get_current_price(self, ticker: str) -> PriceResult:
        t = yf.Ticker(ticker)
        info = t.info
        return PriceResult(
            price=Decimal(str(info["regularMarketPrice"])),
            currency=info.get("currency", "USD"),
        )

    def get_historical_prices(self, ticker: str, start: date, end: date) -> list[PricePoint]:
        t = yf.Ticker(ticker)
        df = t.history(start=str(start), end=str(end))
        return [
            PricePoint(date=row.Index.date(), price=Decimal(str(row.Close)))
            for row in df.itertuples()
        ]
```

- [ ] **Step 5: Implement MarketDataService**

```python
# backend/apps/market_data/services.py
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from apps.instruments.models import Instrument
from .models import PriceCache
from .providers.base import PriceResult, PricePoint
from .providers.yfinance_provider import YFinancePriceProvider

CACHE_TTL = timedelta(minutes=5)

class MarketDataService:
    def __init__(self, provider=None):
        self.provider = provider or YFinancePriceProvider()

    def get_current_price(self, instrument: Instrument) -> PriceResult:
        cache = PriceCache.objects.filter(instrument=instrument).first()
        if cache and (timezone.now() - cache.fetched_at) < CACHE_TTL:
            return PriceResult(price=cache.price, currency=instrument.currency)

        if not instrument.ticker:
            raise ValueError(f"No ticker for instrument {instrument.isin}")

        result = self.provider.get_current_price(instrument.ticker)
        PriceCache.objects.update_or_create(
            instrument=instrument,
            defaults={"price": result.price},
        )
        return result

    def get_historical_prices(
        self, instrument: Instrument, start: date, end: date
    ) -> list[PricePoint]:
        if not instrument.ticker:
            raise ValueError(f"No ticker for instrument {instrument.isin}")
        return self.provider.get_historical_prices(instrument.ticker, start, end)
```

- [ ] **Step 6: Run tests**

```bash
cd backend && python -m pytest apps/market_data/tests/test_services.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/market_data/
git commit -m "feat: add PriceProvider interface, YFinance implementation, MarketDataService with caching"
```

### Task 9: Instrument Resolution Service

**Files:**
- Create: `backend/apps/instruments/services.py`
- Create: `backend/apps/instruments/tests/test_services.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/apps/instruments/tests/test_services.py
import pytest
from unittest.mock import patch, MagicMock
from apps.instruments.models import Instrument
from apps.instruments.services import InstrumentResolver

@pytest.mark.django_db
class TestInstrumentResolver:
    def test_resolve_existing_instrument(self):
        inst = Instrument.objects.create(
            isin="IE00B4L5Y983", ticker="IWDA.AS", name="Test",
            currency="EUR", asset_type="ETF",
        )
        resolver = InstrumentResolver()
        result = resolver.get_or_create("IE00B4L5Y983", name="Test", currency="EUR")
        assert result.id == inst.id

    @patch("apps.instruments.services.yf")
    def test_resolve_new_instrument_from_yfinance(self, mock_yf):
        mock_search = MagicMock()
        mock_search.quotes = [{"symbol": "IWDA.AS", "shortname": "iShares MSCI World"}]
        mock_yf.Search.return_value = mock_search
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "sector": "Diversified",
            "country": "Ireland",
            "quoteType": "ETF",
        }
        mock_yf.Ticker.return_value = mock_ticker

        resolver = InstrumentResolver()
        result = resolver.get_or_create("IE00B4L5Y983", name="Test", currency="EUR")

        assert result.ticker == "IWDA.AS"
        assert result.sector == "Diversified"
        assert result.asset_type == "ETF"

    @patch("apps.instruments.services.yf")
    def test_resolve_unresolvable_instrument(self, mock_yf):
        mock_search = MagicMock()
        mock_search.quotes = []
        mock_yf.Search.return_value = mock_search

        resolver = InstrumentResolver()
        result = resolver.get_or_create("XX0000000000", name="Unknown", currency="EUR")

        assert result.ticker is None
        assert result.isin == "XX0000000000"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest apps/instruments/tests/test_services.py -v
```

- [ ] **Step 3: Implement InstrumentResolver**

```python
# backend/apps/instruments/services.py
import yfinance as yf
from .models import Instrument, AssetType

QUOTE_TYPE_MAP = {
    "EQUITY": AssetType.STOCK,
    "ETF": AssetType.ETF,
    "MUTUALFUND": AssetType.FUND,
    "BOND": AssetType.BOND,
}

class InstrumentResolver:
    def get_or_create(self, isin: str, name: str, currency: str) -> Instrument:
        try:
            return Instrument.objects.get(isin=isin)
        except Instrument.DoesNotExist:
            pass

        ticker, sector, country, asset_type = self._resolve_from_yfinance(isin)

        return Instrument.objects.create(
            isin=isin,
            ticker=ticker,
            name=name,
            currency=currency,
            sector=sector,
            country=country,
            asset_type=asset_type or AssetType.OTHER,
        )

    def _resolve_from_yfinance(self, isin: str):
        try:
            search = yf.Search(isin)
            if not search.quotes:
                return None, None, None, None

            symbol = search.quotes[0]["symbol"]
            info = yf.Ticker(symbol).info
            asset_type = QUOTE_TYPE_MAP.get(info.get("quoteType", ""), None)

            return symbol, info.get("sector"), info.get("country"), asset_type
        except Exception:
            return None, None, None, None
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest apps/instruments/tests/test_services.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/instruments/
git commit -m "feat: add InstrumentResolver with yfinance ISIN-to-ticker lookup"
```

### Task 10: BrokerImporter Abstraction + DeGiro CSV Importer

**Files:**
- Create: `backend/apps/brokers/models.py`
- Create: `backend/apps/brokers/importers/__init__.py`
- Create: `backend/apps/brokers/importers/base.py`
- Create: `backend/apps/brokers/importers/degiro_csv.py`
- Create: `backend/apps/brokers/services.py`
- Create: `backend/apps/brokers/tests/__init__.py`
- Create: `backend/apps/brokers/tests/test_degiro_csv.py`
- Create: `backend/apps/brokers/tests/test_import_service.py`
- Create: `backend/apps/brokers/tests/fixtures/degiro_transactions.csv`

- [ ] **Step 1: Create test CSV fixture**

Create `backend/apps/brokers/tests/fixtures/degiro_transactions.csv` with a sample DeGiro export:
```csv
Date,Time,Product,ISIN,Description,FX,Change,,Balance,,Order ID
13-01-2025,09:15,iShares Core MSCI World,IE00B4L5Y983,Buy 10 @ 75.50 EUR,,EUR,-755.00,EUR,1245.00,12345678
14-01-2025,10:30,iShares Core MSCI World,IE00B4L5Y983,Buy 5 @ 76.00 EUR,,EUR,-380.00,EUR,865.00,12345679
15-01-2025,14:00,ASML Holding,NL0010273215,Buy 2 @ 850.00 EUR,,EUR,-1700.00,EUR,-835.00,12345680
```

Note: The actual DeGiro CSV format should be verified against a real export. The importer will need to handle DeGiro's specific column names and format.

- [ ] **Step 2: Write failing tests for CSV parser**

```python
# backend/apps/brokers/tests/test_degiro_csv.py
import pytest
from pathlib import Path
from decimal import Decimal
from apps.brokers.importers.degiro_csv import DegiroCsvImporter
from apps.brokers.importers.base import TransactionData, TransactionType

FIXTURES = Path(__file__).parent / "fixtures"

class TestDegiroCsvImporter:
    def test_parse_transactions(self):
        importer = DegiroCsvImporter()
        with open(FIXTURES / "degiro_transactions.csv") as f:
            transactions = importer.import_transactions(f)

        assert len(transactions) == 3
        assert transactions[0].isin == "IE00B4L5Y983"
        assert transactions[0].type == TransactionType.BUY
        assert transactions[0].quantity == Decimal("10")
        assert transactions[0].price == Decimal("75.50")

    def test_generates_broker_reference(self):
        importer = DegiroCsvImporter()
        with open(FIXTURES / "degiro_transactions.csv") as f:
            transactions = importer.import_transactions(f)

        refs = [t.broker_reference for t in transactions]
        assert len(set(refs)) == 3  # all unique
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && python -m pytest apps/brokers/tests/test_degiro_csv.py -v
```

- [ ] **Step 4: Implement base types**

```python
# backend/apps/brokers/importers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    FEE = "FEE"
    FX = "FX"

@dataclass
class TransactionData:
    isin: str
    product_name: str
    type: TransactionType
    quantity: Decimal
    price: Decimal
    fee: Decimal
    date: date
    currency: str
    broker_reference: str

class BrokerImporter(ABC):
    broker_name: str = ""

    @abstractmethod
    def import_transactions(self, source) -> list[TransactionData]: ...
```

- [ ] **Step 5: Implement DeGiro CSV importer**

```python
# backend/apps/brokers/importers/degiro_csv.py
import csv
import hashlib
import re
from datetime import datetime
from decimal import Decimal
from io import TextIOWrapper
from .base import BrokerImporter, TransactionData, TransactionType

class DegiroCsvImporter(BrokerImporter):
    broker_name = "degiro"

    def import_transactions(self, source) -> list[TransactionData]:
        reader = csv.DictReader(source)
        transactions = []

        for row in reader:
            parsed = self._parse_row(row)
            if parsed:
                transactions.append(parsed)

        return transactions

    def _parse_row(self, row: dict) -> TransactionData | None:
        description = row.get("Description", "")
        isin = row.get("ISIN", "").strip()

        if not isin:
            return None

        tx_type, quantity, price = self._parse_description(description)
        if tx_type is None:
            return None

        date_str = row.get("Date", "")
        tx_date = datetime.strptime(date_str, "%d-%m-%Y").date()

        currency = row.get("Change", "").strip() or "EUR"
        # Find the currency column (DeGiro has unnamed columns)
        for key, val in row.items():
            if key and key.startswith("Change"):
                currency = val.strip() if val.strip() else currency
                break

        broker_ref = self._make_reference(isin, tx_date, quantity, price, row.get("Order ID", ""))

        return TransactionData(
            isin=isin,
            product_name=row.get("Product", ""),
            type=tx_type,
            quantity=quantity,
            price=price,
            fee=Decimal("0"),  # DeGiro fee rows are separate
            date=tx_date,
            currency=currency,
            broker_reference=broker_ref,
        )

    def _parse_description(self, desc: str):
        buy_match = re.match(r"Buy (\d+(?:\.\d+)?) @ ([\d.]+)", desc)
        if buy_match:
            return TransactionType.BUY, Decimal(buy_match.group(1)), Decimal(buy_match.group(2))

        sell_match = re.match(r"Sell (\d+(?:\.\d+)?) @ ([\d.]+)", desc)
        if sell_match:
            return TransactionType.SELL, Decimal(sell_match.group(1)), Decimal(sell_match.group(2))

        if "Dividend" in desc:
            return TransactionType.DIVIDEND, Decimal("0"), Decimal("0")

        return None, None, None

    def _make_reference(self, isin, date, quantity, price, order_id):
        raw = f"degiro:{isin}:{date}:{quantity}:{price}:{order_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
```

Note: The DeGiro CSV format varies by language/region. This implementation parses the English format. The real format should be verified against an actual export and adjusted accordingly.

- [ ] **Step 6: Run tests**

```bash
cd backend && python -m pytest apps/brokers/tests/test_degiro_csv.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/apps/brokers/
git commit -m "feat: add BrokerImporter abstraction and DeGiro CSV importer"
```

### Task 11: Import Service (Dedup, Instrument Resolution, Holdings Recalc)

**Files:**
- Create: `backend/apps/brokers/services.py`
- Create: `backend/apps/brokers/tests/test_import_service.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/apps/brokers/tests/test_import_service.py
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock
from apps.users.models import User
from apps.instruments.models import Instrument
from apps.portfolios.models import Portfolio, Transaction, Holding
from apps.brokers.importers.base import TransactionData, TransactionType
from apps.brokers.services import ImportService

@pytest.mark.django_db
class TestImportService:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.portfolio = Portfolio.objects.create(user=self.user, name="Main")
        self.instrument = Instrument.objects.create(
            isin="IE00B4L5Y983", ticker="IWDA.AS", name="MSCI World",
            currency="EUR", asset_type="ETF",
        )

    def _make_tx(self, quantity="10", price="75.50", ref="ref1"):
        return TransactionData(
            isin="IE00B4L5Y983", product_name="MSCI World",
            type=TransactionType.BUY, quantity=Decimal(quantity),
            price=Decimal(price), fee=Decimal("2.00"),
            date=date(2025, 1, 15), currency="EUR",
            broker_reference=ref,
        )

    @patch("apps.brokers.services.InstrumentResolver")
    def test_import_creates_transactions(self, MockResolver):
        MockResolver.return_value.get_or_create.return_value = self.instrument

        service = ImportService()
        result = service.import_transactions(self.portfolio, [self._make_tx()])

        assert result.imported == 1
        assert result.skipped == 0
        assert Transaction.objects.filter(portfolio=self.portfolio).count() == 1

    @patch("apps.brokers.services.InstrumentResolver")
    def test_import_skips_duplicates(self, MockResolver):
        MockResolver.return_value.get_or_create.return_value = self.instrument

        service = ImportService()
        service.import_transactions(self.portfolio, [self._make_tx()])
        result = service.import_transactions(self.portfolio, [self._make_tx()])

        assert result.imported == 0
        assert result.skipped == 1
        assert Transaction.objects.filter(portfolio=self.portfolio).count() == 1

    @patch("apps.brokers.services.InstrumentResolver")
    def test_import_recalculates_holdings(self, MockResolver):
        MockResolver.return_value.get_or_create.return_value = self.instrument

        service = ImportService()
        service.import_transactions(self.portfolio, [
            self._make_tx(quantity="10", price="75.50", ref="ref1"),
            self._make_tx(quantity="5", price="76.00", ref="ref2"),
        ])

        holding = Holding.objects.get(portfolio=self.portfolio, instrument=self.instrument)
        assert holding.quantity == Decimal("15")
        # avg_buy_price = (10*75.50 + 5*76.00) / 15 = 75.6667
        assert abs(holding.avg_buy_price - Decimal("75.6667")) < Decimal("0.001")

    @patch("apps.brokers.services.InstrumentResolver")
    def test_import_sell_reduces_holding(self, MockResolver):
        MockResolver.return_value.get_or_create.return_value = self.instrument

        service = ImportService()
        service.import_transactions(self.portfolio, [
            self._make_tx(quantity="10", price="75.50", ref="ref1"),
        ])
        sell_tx = TransactionData(
            isin="IE00B4L5Y983", product_name="MSCI World",
            type=TransactionType.SELL, quantity=Decimal("4"),
            price=Decimal("80.00"), fee=Decimal("2.00"),
            date=date(2025, 1, 20), currency="EUR",
            broker_reference="ref_sell",
        )
        service.import_transactions(self.portfolio, [sell_tx])

        holding = Holding.objects.get(portfolio=self.portfolio, instrument=self.instrument)
        assert holding.quantity == Decimal("6")
        assert holding.avg_buy_price == Decimal("75.50")  # avg unchanged after sell

    @patch("apps.brokers.services.InstrumentResolver")
    def test_import_full_sell_deletes_holding(self, MockResolver):
        MockResolver.return_value.get_or_create.return_value = self.instrument

        service = ImportService()
        service.import_transactions(self.portfolio, [
            self._make_tx(quantity="10", price="75.50", ref="ref1"),
        ])
        sell_tx = TransactionData(
            isin="IE00B4L5Y983", product_name="MSCI World",
            type=TransactionType.SELL, quantity=Decimal("10"),
            price=Decimal("80.00"), fee=Decimal("2.00"),
            date=date(2025, 1, 20), currency="EUR",
            broker_reference="ref_sell_all",
        )
        service.import_transactions(self.portfolio, [sell_tx])

        assert not Holding.objects.filter(portfolio=self.portfolio, instrument=self.instrument).exists()

    @patch("apps.brokers.services.InstrumentResolver")
    def test_import_is_atomic(self, MockResolver):
        # Second transaction triggers an error
        MockResolver.return_value.get_or_create.side_effect = [
            self.instrument,
            Exception("resolution failed"),
        ]

        service = ImportService()
        with pytest.raises(Exception):
            service.import_transactions(self.portfolio, [
                self._make_tx(ref="ref1"),
                self._make_tx(ref="ref2"),
            ])

        assert Transaction.objects.filter(portfolio=self.portfolio).count() == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest apps/brokers/tests/test_import_service.py -v
```

- [ ] **Step 3: Implement ImportService**

```python
# backend/apps/brokers/services.py
from dataclasses import dataclass
from decimal import Decimal
from django.db import transaction as db_transaction
from apps.instruments.services import InstrumentResolver
from apps.portfolios.models import Portfolio, Transaction, Holding, TransactionType
from .importers.base import TransactionData

@dataclass
class ImportResult:
    imported: int
    skipped: int
    warnings: list[str]

class ImportService:
    def __init__(self, resolver=None):
        self.resolver = resolver or InstrumentResolver()

    @db_transaction.atomic
    def import_transactions(self, portfolio: Portfolio, data: list[TransactionData]) -> ImportResult:
        imported = 0
        skipped = 0
        warnings = []
        instruments_touched = set()

        for tx_data in data:
            if Transaction.objects.filter(
                portfolio=portfolio, broker_reference=tx_data.broker_reference
            ).exists():
                skipped += 1
                continue

            instrument = self.resolver.get_or_create(
                isin=tx_data.isin, name=tx_data.product_name, currency=tx_data.currency,
            )

            if not instrument.ticker:
                warnings.append(f"Unresolved ticker for {tx_data.isin} ({tx_data.product_name})")

            Transaction.objects.create(
                portfolio=portfolio,
                instrument=instrument,
                type=tx_data.type.value,
                quantity=tx_data.quantity,
                price=tx_data.price,
                fee=tx_data.fee,
                date=tx_data.date,
                broker_source="degiro",
                broker_reference=tx_data.broker_reference,
            )
            instruments_touched.add(instrument.id)
            imported += 1

        # Recalculate holdings for touched instruments
        for instrument_id in instruments_touched:
            self._recalculate_holding(portfolio, instrument_id)

        return ImportResult(imported=imported, skipped=skipped, warnings=warnings)

    def _recalculate_holding(self, portfolio: Portfolio, instrument_id: int):
        txs = Transaction.objects.filter(
            portfolio=portfolio, instrument_id=instrument_id,
        ).order_by("date")

        total_qty = Decimal("0")
        total_cost = Decimal("0")

        for tx in txs:
            if tx.type == TransactionType.BUY:
                total_qty += tx.quantity
                total_cost += tx.quantity * tx.price
            elif tx.type == TransactionType.SELL:
                # Reduce cost by avg cost basis of sold shares, not sell price
                if total_qty > 0:
                    avg_cost = total_cost / total_qty
                    total_cost -= tx.quantity * avg_cost
                total_qty -= tx.quantity

        if total_qty > 0:
            avg_price = total_cost / total_qty
            Holding.objects.update_or_create(
                portfolio=portfolio, instrument_id=instrument_id,
                defaults={"quantity": total_qty, "avg_buy_price": avg_price},
            )
        else:
            Holding.objects.filter(
                portfolio=portfolio, instrument_id=instrument_id,
            ).delete()
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest apps/brokers/tests/test_import_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/brokers/services.py backend/apps/brokers/tests/test_import_service.py
git commit -m "feat: add ImportService with dedup, instrument resolution, and holdings recalc"
```

### Task 12: BrokerConnection Model

**Files:**
- Modify: `backend/apps/brokers/models.py`

- [ ] **Step 1: Implement BrokerConnection model**

```python
# backend/apps/brokers/models.py
from django.db import models
from django.conf import settings

class BrokerType(models.TextChoices):
    DEGIRO = "degiro"

class BrokerConnection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="broker_connections")
    broker_type = models.CharField(max_length=20, choices=BrokerType.choices)
    credentials_encrypted = models.TextField()  # JSON, encrypted at rest
    last_sync = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "broker_type"]
```

- [ ] **Step 2: Migrate and commit**

```bash
cd backend && python manage.py makemigrations brokers && python manage.py migrate
git add backend/apps/brokers/
git commit -m "feat: add BrokerConnection model"
```

---

## Chunk 4: Backend API Endpoints

### Task 13: Portfolio CRUD API

**Files:**
- Create: `backend/apps/portfolios/serializers.py`
- Create: `backend/apps/portfolios/views.py`
- Create: `backend/apps/portfolios/urls.py`
- Create: `backend/apps/portfolios/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/apps/portfolios/tests/test_api.py
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.models import User
from apps.portfolios.models import Portfolio

@pytest.mark.django_db
class TestPortfolioAPI:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_portfolio(self):
        resp = self.client.post("/api/portfolios/", {"name": "Main"})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "Main"

    def test_list_portfolios(self):
        Portfolio.objects.create(user=self.user, name="Main")
        Portfolio.objects.create(user=self.user, name="Speculative")
        resp = self.client.get("/api/portfolios/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 2

    def test_list_portfolios_only_own(self):
        other = User.objects.create_user(username="other", password="pass12345")
        Portfolio.objects.create(user=self.user, name="Mine")
        Portfolio.objects.create(user=other, name="Theirs")
        resp = self.client.get("/api/portfolios/")
        assert len(resp.data["results"]) == 1

    def test_delete_portfolio(self):
        p = Portfolio.objects.create(user=self.user, name="Main")
        resp = self.client.delete(f"/api/portfolios/{p.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest apps/portfolios/tests/test_api.py -v
```

- [ ] **Step 3: Implement serializers, views, urls**

```python
# backend/apps/portfolios/serializers.py
from rest_framework import serializers
from .models import Portfolio, Holding, Transaction
from apps.instruments.serializers import InstrumentSerializer

class PortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portfolio
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]

class HoldingSerializer(serializers.ModelSerializer):
    instrument = InstrumentSerializer(read_only=True)

    class Meta:
        model = Holding
        fields = ["id", "instrument", "quantity", "avg_buy_price"]

class TransactionSerializer(serializers.ModelSerializer):
    instrument = InstrumentSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id", "instrument", "type", "quantity", "price",
            "fee", "date", "broker_source", "broker_reference",
        ]
```

```python
# backend/apps/portfolios/views.py
from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Portfolio, Holding, Transaction
from .serializers import PortfolioSerializer, HoldingSerializer, TransactionSerializer

class PortfolioViewSet(viewsets.ModelViewSet):
    serializer_class = PortfolioSerializer

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class HoldingListView(generics.ListAPIView):
    serializer_class = HoldingSerializer

    def get_queryset(self):
        return Holding.objects.filter(
            portfolio_id=self.kwargs["portfolio_id"],
            portfolio__user=self.request.user,
        ).select_related("instrument")

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    filterset_fields = ["type", "instrument__ticker"]
    ordering_fields = ["date", "type"]

    def get_queryset(self):
        if "portfolio_id" in self.kwargs:
            return Transaction.objects.filter(
                portfolio_id=self.kwargs["portfolio_id"],
                portfolio__user=self.request.user,
            ).select_related("instrument")
        return Transaction.objects.filter(
            portfolio__user=self.request.user,
        ).select_related("instrument")
```

```python
# backend/apps/portfolios/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PortfolioViewSet, HoldingListView, TransactionViewSet

router = DefaultRouter()
router.register(r"portfolios", PortfolioViewSet, basename="portfolio")

urlpatterns = [
    path("", include(router.urls)),
    path("portfolios/<int:portfolio_id>/holdings/", HoldingListView.as_view(), name="portfolio-holdings"),
    path(
        "portfolios/<int:portfolio_id>/transactions/",
        TransactionViewSet.as_view({"get": "list", "post": "create"}),
        name="portfolio-transactions",
    ),
    path("transactions/<int:pk>/", TransactionViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}), name="transaction-detail"),
]
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest apps/portfolios/tests/test_api.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/portfolios/
git commit -m "feat: add Portfolio CRUD, Holdings list, Transaction CRUD API endpoints"
```

### Task 14: Portfolio Summary, Performance, Allocation Endpoints

**Files:**
- Modify: `backend/apps/portfolios/views.py`
- Create: `backend/apps/portfolios/tests/test_analytics.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/apps/portfolios/tests/test_analytics.py
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.models import User
from apps.instruments.models import Instrument
from apps.portfolios.models import Portfolio, Holding, Transaction, TransactionType
from apps.market_data.providers.base import PriceResult, PricePoint

@pytest.mark.django_db
class TestPortfolioAnalytics:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.portfolio = Portfolio.objects.create(user=self.user, name="Main")
        self.inst = Instrument.objects.create(
            isin="IE00B4L5Y983", ticker="IWDA.AS", name="MSCI World",
            currency="EUR", asset_type="ETF", sector="Diversified", country="Ireland",
        )
        Holding.objects.create(
            portfolio=self.portfolio, instrument=self.inst,
            quantity=Decimal("10"), avg_buy_price=Decimal("75.50"),
        )

    @patch("apps.portfolios.views.MarketDataService")
    def test_summary(self, MockService):
        MockService.return_value.get_current_price.return_value = PriceResult(
            price=Decimal("80.00"), currency="EUR",
        )
        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/summary/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["total_value"] == "800.00"
        assert resp.data["total_gain_loss"] == "45.00"  # (80-75.50)*10

    @patch("apps.portfolios.views.MarketDataService")
    def test_performance(self, MockService):
        Transaction.objects.create(
            portfolio=self.portfolio, instrument=self.inst,
            type=TransactionType.BUY, quantity=Decimal("10"),
            price=Decimal("75.50"), fee=Decimal("0"),
            date=date(2025, 1, 1), broker_source="degiro",
            broker_reference="ref1",
        )
        MockService.return_value.get_historical_prices.return_value = [
            PricePoint(date=date(2025, 1, 1), price=Decimal("75.50")),
            PricePoint(date=date(2025, 1, 2), price=Decimal("76.00")),
        ]
        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/performance/?period=1W")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["series"]) > 0

    def test_allocation_by_sector(self):
        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/allocation/?group_by=sector")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) > 0
        assert resp.data[0]["group"] == "Diversified"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest apps/portfolios/tests/test_analytics.py -v
```

- [ ] **Step 3: Add summary, performance, allocation views**

Add to `backend/apps/portfolios/views.py`:

```python
from datetime import date, timedelta
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.market_data.services import MarketDataService

class PortfolioSummaryView(APIView):
    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        holdings = portfolio.holdings.select_related("instrument").all()
        service = MarketDataService()

        total_value = Decimal("0")
        total_cost = Decimal("0")

        for h in holdings:
            price_result = service.get_current_price(h.instrument)
            total_value += h.quantity * price_result.price
            total_cost += h.quantity * h.avg_buy_price

        return Response({
            "total_value": f"{total_value:.2f}",
            "total_cost": f"{total_cost:.2f}",
            "total_gain_loss": f"{total_value - total_cost:.2f}",
            "total_return_pct": f"{((total_value - total_cost) / total_cost * 100):.2f}" if total_cost else "0",
        })

PERIOD_MAP = {
    "1W": timedelta(weeks=1),
    "1M": timedelta(days=30),
    "3M": timedelta(days=90),
    "6M": timedelta(days=180),
    "1Y": timedelta(days=365),
}

class PortfolioPerformanceView(APIView):
    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        period = request.query_params.get("period", "1M")
        service = MarketDataService()

        if period == "ALL":
            first_tx = portfolio.transactions.order_by("date").first()
            start = first_tx.date if first_tx else date.today()
        else:
            delta = PERIOD_MAP.get(period, timedelta(days=30))
            start = date.today() - delta

        end = date.today()

        # Reconstruct holdings at each date from transactions
        txs = portfolio.transactions.select_related("instrument").order_by("date").all()

        # Build a map of instrument -> list of (date, qty_change)
        instrument_changes = {}
        for tx in txs:
            if not tx.instrument.ticker:
                continue
            changes = instrument_changes.setdefault(tx.instrument_id, {
                "instrument": tx.instrument, "events": []
            })
            if tx.type == TransactionType.BUY:
                changes["events"].append((tx.date, tx.quantity))
            elif tx.type == TransactionType.SELL:
                changes["events"].append((tx.date, -tx.quantity))

        # For each instrument, get historical prices and compute daily value
        series_map = {}
        for inst_data in instrument_changes.values():
            instrument = inst_data["instrument"]
            events = inst_data["events"]
            prices = service.get_historical_prices(instrument, start, end)

            # Build qty held at each price date
            qty = Decimal("0")
            event_idx = 0
            for pp in prices:
                # Apply all events up to this date
                while event_idx < len(events) and events[event_idx][0] <= pp.date:
                    qty += events[event_idx][1]
                    event_idx += 1
                if qty > 0:
                    series_map.setdefault(pp.date, Decimal("0"))
                    series_map[pp.date] += qty * pp.price

        series = [
            {"date": str(d), "value": f"{v:.2f}"}
            for d, v in sorted(series_map.items())
        ]

        return Response({"series": series})

class PortfolioAllocationView(APIView):
    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        group_by = request.query_params.get("group_by", "sector")
        holdings = portfolio.holdings.select_related("instrument").all()

        groups = {}
        for h in holdings:
            key = getattr(h.instrument, group_by, "Unknown") or "Unknown"
            groups.setdefault(key, Decimal("0"))
            groups[key] += h.quantity * h.avg_buy_price  # use cost basis for allocation

        total = sum(groups.values())
        result = [
            {
                "group": k,
                "value": f"{v:.2f}",
                "percentage": f"{(v / total * 100):.1f}" if total else "0",
            }
            for k, v in sorted(groups.items(), key=lambda x: -x[1])
        ]

        return Response(result)
```

Add to `backend/apps/portfolios/urls.py`:
```python
path("portfolios/<int:portfolio_id>/summary/", PortfolioSummaryView.as_view(), name="portfolio-summary"),
path("portfolios/<int:portfolio_id>/performance/", PortfolioPerformanceView.as_view(), name="portfolio-performance"),
path("portfolios/<int:portfolio_id>/allocation/", PortfolioAllocationView.as_view(), name="portfolio-allocation"),
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest apps/portfolios/tests/test_analytics.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/portfolios/
git commit -m "feat: add portfolio summary, performance, and allocation endpoints"
```

### Task 15: Import API Endpoints

**Files:**
- Create: `backend/apps/brokers/views.py`
- Create: `backend/apps/brokers/serializers.py`
- Create: `backend/apps/brokers/urls.py`
- Create: `backend/apps/brokers/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/apps/brokers/tests/test_api.py
import pytest
from io import BytesIO
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from apps.users.models import User
from apps.portfolios.models import Portfolio
from apps.instruments.models import Instrument

@pytest.mark.django_db
class TestImportAPI:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.portfolio = Portfolio.objects.create(user=self.user, name="Main")

    def test_csv_preview(self):
        csv_content = b"Date,Time,Product,ISIN,Description,FX,Change,,Balance,,Order ID\n"
        csv_content += b"13-01-2025,09:15,MSCI World,IE00B4L5Y983,Buy 10 @ 75.50 EUR,,EUR,-755.00,EUR,1245.00,12345678\n"
        f = BytesIO(csv_content)
        f.name = "transactions.csv"

        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/",
            {"file": f, "broker": "degiro"},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "transactions" in resp.data
        assert len(resp.data["transactions"]) == 1
        assert "preview_id" in resp.data

    @patch("apps.brokers.views.ImportService")
    def test_csv_confirm(self, MockService):
        MockService.return_value.import_transactions.return_value = MagicMock(
            imported=1, skipped=0, warnings=[],
        )
        # First, do a preview to get a preview_id
        # Then confirm it. For simplicity, test the confirm endpoint directly.
        from django.core.cache import cache
        from apps.brokers.importers.base import TransactionData, TransactionType
        from decimal import Decimal
        from datetime import date

        preview_data = [TransactionData(
            isin="IE00B4L5Y983", product_name="Test",
            type=TransactionType.BUY, quantity=Decimal("10"),
            price=Decimal("75.50"), fee=Decimal("0"),
            date=date(2025, 1, 15), currency="EUR",
            broker_reference="ref1",
        )]
        cache.set("import_preview_test_1", preview_data, timeout=600)

        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/confirm/",
            {"preview_id": "test_1"},
        )
        assert resp.status_code == status.HTTP_200_OK
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest apps/brokers/tests/test_api.py -v
```

- [ ] **Step 3: Implement views, serializers, urls**

```python
# backend/apps/brokers/serializers.py
from rest_framework import serializers
from .models import BrokerConnection

class BrokerConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerConnection
        fields = ["id", "broker_type", "last_sync", "created_at"]
        read_only_fields = ["id", "last_sync", "created_at"]
```

```python
# backend/apps/brokers/views.py
import uuid
from io import TextIOWrapper
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from apps.portfolios.models import Portfolio
from .models import BrokerConnection
from .serializers import BrokerConnectionSerializer
from .importers.degiro_csv import DegiroCsvImporter
from .services import ImportService

IMPORTERS = {
    "degiro": DegiroCsvImporter,
}

class BrokerConnectionViewSet(viewsets.ModelViewSet):
    serializer_class = BrokerConnectionSerializer
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return BrokerConnection.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CsvPreviewView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        broker = request.data.get("broker", "degiro")
        file = request.FILES.get("file")

        if not file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        importer_cls = IMPORTERS.get(broker)
        if not importer_cls:
            return Response({"error": f"Unknown broker: {broker}"}, status=status.HTTP_400_BAD_REQUEST)

        importer = importer_cls()
        text_file = TextIOWrapper(file, encoding="utf-8")
        transactions = importer.import_transactions(text_file)

        preview_id = f"{request.user.id}_{uuid.uuid4().hex[:8]}"
        cache.set(f"import_preview_{preview_id}", transactions, timeout=600)

        return Response({
            "preview_id": preview_id,
            "transactions": [
                {
                    "isin": t.isin,
                    "product_name": t.product_name,
                    "type": t.type.value,
                    "quantity": str(t.quantity),
                    "price": str(t.price),
                    "date": str(t.date),
                    "currency": t.currency,
                }
                for t in transactions
            ],
        })

class CsvConfirmView(APIView):
    def post(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        preview_id = request.data.get("preview_id")

        transactions = cache.get(f"import_preview_{preview_id}")
        if transactions is None:
            return Response({"error": "Preview expired"}, status=status.HTTP_400_BAD_REQUEST)

        service = ImportService()
        result = service.import_transactions(portfolio, transactions)
        cache.delete(f"import_preview_{preview_id}")

        return Response({
            "imported": result.imported,
            "skipped": result.skipped,
            "warnings": result.warnings,
        })
```

```python
# backend/apps/brokers/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BrokerConnectionViewSet, CsvPreviewView, CsvConfirmView

router = DefaultRouter()
router.register(r"broker-connections", BrokerConnectionViewSet, basename="broker-connection")

urlpatterns = [
    path("", include(router.urls)),
    path("portfolios/<int:portfolio_id>/import/csv/", CsvPreviewView.as_view(), name="import-csv-preview"),
    path("portfolios/<int:portfolio_id>/import/csv/confirm/", CsvConfirmView.as_view(), name="import-csv-confirm"),
]
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest apps/brokers/tests/test_api.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/apps/brokers/
git commit -m "feat: add CSV import preview/confirm and broker connection API endpoints"
```

### Task 16: Market Data API Endpoint

**Files:**
- Create: `backend/apps/market_data/views.py`
- Create: `backend/apps/market_data/urls.py`
- Create: `backend/apps/market_data/tests/test_api.py`

- [ ] **Step 1: Write failing test**

```python
# backend/apps/market_data/tests/test_api.py
import pytest
from decimal import Decimal
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.models import User
from apps.instruments.models import Instrument
from apps.market_data.providers.base import PriceResult

@pytest.mark.django_db
class TestPriceAPI:
    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.inst = Instrument.objects.create(
            isin="IE00B4L5Y983", ticker="IWDA.AS", name="Test",
            currency="EUR", asset_type="ETF",
        )

    @patch("apps.market_data.views.MarketDataService")
    def test_get_price(self, MockService):
        MockService.return_value.get_current_price.return_value = PriceResult(
            price=Decimal("75.50"), currency="EUR",
        )
        resp = self.client.get("/api/prices/IWDA.AS/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["price"] == "75.50"
```

- [ ] **Step 2: Implement**

```python
# backend/apps/market_data/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.instruments.models import Instrument
from .services import MarketDataService

class PriceView(APIView):
    def get(self, request, ticker):
        try:
            instrument = Instrument.objects.get(ticker=ticker)
        except Instrument.DoesNotExist:
            return Response({"error": "Instrument not found"}, status=status.HTTP_404_NOT_FOUND)

        service = MarketDataService()
        result = service.get_current_price(instrument)

        return Response({
            "ticker": ticker,
            "price": f"{result.price:.2f}",
            "currency": result.currency,
        })
```

```python
# backend/apps/market_data/urls.py
from django.urls import path
from .views import PriceView

urlpatterns = [
    path("prices/<str:ticker>/", PriceView.as_view(), name="price"),
]
```

- [ ] **Step 3: Run tests**

```bash
cd backend && python -m pytest apps/market_data/tests/test_api.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/apps/market_data/
git commit -m "feat: add price lookup API endpoint"
```

### Task 17: Currency Conversion Service

**Files:**
- Create: `backend/apps/market_data/currency.py`
- Create: `backend/apps/market_data/tests/test_currency.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/apps/market_data/tests/test_currency.py
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from apps.market_data.currency import CurrencyConverter

class TestCurrencyConverter:
    @patch("apps.market_data.currency.yf")
    def test_convert_eur_to_usd(self, mock_yf):
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 1.08}
        mock_yf.Ticker.return_value = mock_ticker

        converter = CurrencyConverter()
        result = converter.convert(Decimal("100"), "EUR", "USD")
        assert result == Decimal("108.00")

    def test_same_currency_no_conversion(self):
        converter = CurrencyConverter()
        result = converter.convert(Decimal("100"), "EUR", "EUR")
        assert result == Decimal("100")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest apps/market_data/tests/test_currency.py -v
```

- [ ] **Step 3: Implement CurrencyConverter**

```python
# backend/apps/market_data/currency.py
import yfinance as yf
from decimal import Decimal
from functools import lru_cache

class CurrencyConverter:
    def convert(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        if from_currency == to_currency:
            return amount
        rate = self._get_rate(from_currency, to_currency)
        return (amount * rate).quantize(Decimal("0.01"))

    @lru_cache(maxsize=64)
    def _get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        symbol = f"{from_currency}{to_currency}=X"
        ticker = yf.Ticker(symbol)
        price = ticker.info.get("regularMarketPrice", 1.0)
        return Decimal(str(price))
```

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest apps/market_data/tests/test_currency.py -v
```

Expected: PASS.

- [ ] **Step 5: Integrate into PortfolioSummaryView**

Update `PortfolioSummaryView` and `PortfolioAllocationView` to convert each holding's value from `instrument.currency` to the user's `base_currency` using `CurrencyConverter`.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/market_data/
git commit -m "feat: add CurrencyConverter and integrate with portfolio views"
```

### Task 17b: DeGiro API Importer (Stub)

**Files:**
- Create: `backend/apps/brokers/importers/degiro_api.py`
- Modify: `backend/apps/brokers/views.py` (add sync endpoint)
- Modify: `backend/apps/brokers/urls.py`

- [ ] **Step 1: Implement DegiroApiImporter**

```python
# backend/apps/brokers/importers/degiro_api.py
from .base import BrokerImporter, TransactionData

class DegiroApiImporter(BrokerImporter):
    broker_name = "degiro"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def import_transactions(self, source=None) -> list[TransactionData]:
        # TODO: implement via degiro-connector
        # For v1, this is a stub that raises NotImplementedError
        raise NotImplementedError("DeGiro API sync coming soon")
```

- [ ] **Step 2: Add sync endpoint**

Add `ImportSyncView` to `backend/apps/brokers/views.py`:
```python
class ImportSyncView(APIView):
    def post(self, request, portfolio_id):
        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        return Response(
            {"error": "API sync not yet implemented"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
```

Add to `backend/apps/brokers/urls.py`:
```python
path("portfolios/<int:portfolio_id>/import/sync/", ImportSyncView.as_view(), name="import-sync"),
```

- [ ] **Step 3: Commit**

```bash
git add backend/apps/brokers/
git commit -m "feat: add DeGiro API importer stub and sync endpoint"
```

---

## Chunk 5: Frontend Auth & Layout

### Task 18: TypeScript Types

**Files:**
- Create: `frontend/src/types/api.ts`

- [ ] **Step 1: Define shared types**

```typescript
// frontend/src/types/api.ts
export interface User {
  id: number;
  username: string;
  email: string;
  base_currency: string;
}

export interface Instrument {
  id: number;
  isin: string;
  ticker: string | null;
  name: string;
  currency: string;
  sector: string | null;
  country: string | null;
  asset_type: string;
}

export interface Portfolio {
  id: number;
  name: string;
  created_at: string;
}

export interface Holding {
  id: number;
  instrument: Instrument;
  quantity: string;
  avg_buy_price: string;
}

export interface Transaction {
  id: number;
  instrument: Instrument;
  type: "BUY" | "SELL" | "DIVIDEND" | "FEE" | "FX";
  quantity: string;
  price: string;
  fee: string;
  date: string;
  broker_source: string;
  broker_reference: string;
}

export interface PortfolioSummary {
  total_value: string;
  total_cost: string;
  total_gain_loss: string;
  total_return_pct: string;
}

export interface PerformanceSeries {
  series: { date: string; value: string }[];
}

export interface AllocationItem {
  group: string;
  value: string;
  percentage: string;
}

export interface PaginatedResponse<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ImportPreview {
  preview_id: string;
  transactions: {
    isin: string;
    product_name: string;
    type: string;
    quantity: string;
    price: string;
    date: string;
    currency: string;
  }[];
}

export interface ImportResult {
  imported: number;
  skipped: number;
  warnings: string[];
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/
git commit -m "feat: add TypeScript API types"
```

### Task 19: API Client Functions

**Files:**
- Create: `frontend/src/lib/api/auth.ts`
- Create: `frontend/src/lib/api/portfolios.ts`
- Create: `frontend/src/lib/api/import.ts`

- [ ] **Step 1: Auth API**

```typescript
// frontend/src/lib/api/auth.ts
import { apiClient } from "./client";
import type { User } from "@/types/api";

export async function register(data: { username: string; email: string; password: string }) {
  return apiClient<User>("/auth/register/", { method: "POST", body: data });
}

export async function login(data: { username: string; password: string }) {
  const res = await apiClient<{ access: string; refresh: string }>("/auth/login/", {
    method: "POST",
    body: data,
  });
  localStorage.setItem("access_token", res.access);
  localStorage.setItem("refresh_token", res.refresh);
  return res;
}

export async function getMe() {
  return apiClient<User>("/user/me/");
}

export async function updateMe(data: Partial<User>) {
  return apiClient<User>("/user/me/", { method: "PATCH", body: data });
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}
```

- [ ] **Step 2: Portfolios API**

```typescript
// frontend/src/lib/api/portfolios.ts
import { apiClient } from "./client";
import type {
  Portfolio, Holding, Transaction, PortfolioSummary,
  PerformanceSeries, AllocationItem, PaginatedResponse,
} from "@/types/api";

export async function listPortfolios() {
  return apiClient<PaginatedResponse<Portfolio>>("/portfolios/");
}

export async function createPortfolio(name: string) {
  return apiClient<Portfolio>("/portfolios/", { method: "POST", body: { name } });
}

export async function deletePortfolio(id: number) {
  return apiClient<void>(`/portfolios/${id}/`, { method: "DELETE" });
}

export async function getHoldings(portfolioId: number) {
  return apiClient<PaginatedResponse<Holding>>(`/portfolios/${portfolioId}/holdings/`);
}

export async function getSummary(portfolioId: number) {
  return apiClient<PortfolioSummary>(`/portfolios/${portfolioId}/summary/`);
}

export async function getPerformance(portfolioId: number, period: string) {
  return apiClient<PerformanceSeries>(`/portfolios/${portfolioId}/performance/?period=${period}`);
}

export async function getAllocation(portfolioId: number, groupBy: string) {
  return apiClient<AllocationItem[]>(`/portfolios/${portfolioId}/allocation/?group_by=${groupBy}`);
}

export async function getTransactions(portfolioId: number) {
  return apiClient<PaginatedResponse<Transaction>>(`/portfolios/${portfolioId}/transactions/`);
}
```

- [ ] **Step 3: Import API**

```typescript
// frontend/src/lib/api/import.ts
import type { ImportPreview, ImportResult } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export async function uploadCsv(
  portfolioId: number,
  file: File,
  broker: string
): Promise<ImportPreview> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("broker", broker);

  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/import/csv/`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function confirmImport(
  portfolioId: number,
  previewId: string
): Promise<ImportResult> {
  const { apiClient } = await import("./client");
  return apiClient<ImportResult>(`/portfolios/${portfolioId}/import/csv/confirm/`, {
    method: "POST",
    body: { preview_id: previewId },
  });
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api/
git commit -m "feat: add typed API client functions for auth, portfolios, and import"
```

### Task 20: Auth Pages (Login + Register)

**Files:**
- Create: `frontend/src/app/(auth)/login/page.tsx`
- Create: `frontend/src/app/(auth)/register/page.tsx`
- Create: `frontend/src/lib/auth-context.tsx`

- [ ] **Step 1: Install shadcn components needed**

```bash
cd frontend
npx shadcn@latest add button input label card
```

- [ ] **Step 2: Create auth context**

```typescript
// frontend/src/lib/auth-context.tsx
"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import type { User } from "@/types/api";
import { getMe, logout as apiLogout } from "./api/auth";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  refreshUser: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const u = await getMe();
      setUser(u);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    apiLogout();
    setUser(null);
  };

  useEffect(() => { refreshUser(); }, []);

  return (
    <AuthContext.Provider value={{ user, loading, refreshUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

- [ ] **Step 3: Create login page**

```typescript
// frontend/src/app/(auth)/login/page.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();
  const { refreshUser } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await login({ username, password });
      await refreshUser();
      router.push("/dashboard");
    } catch {
      setError("Invalid credentials");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Login</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="username">Username</Label>
              <Input id="username" value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
            {error && <p className="text-sm text-red-500">{error}</p>}
            <Button type="submit" className="w-full">Login</Button>
            <p className="text-sm text-center">
              No account? <Link href="/register" className="underline">Register</Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 4: Create register page**

Same pattern as login, but calls `register()` then redirects to `/login`.

- [ ] **Step 5: Update layout to include AuthProvider**

Wrap the `Providers` component to also include `<AuthProvider>`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: add auth context, login and register pages"
```

### Task 21: App Layout with Navigation

**Files:**
- Create: `frontend/src/components/layout/sidebar.tsx`
- Create: `frontend/src/components/layout/app-layout.tsx`

- [ ] **Step 1: Install shadcn nav components**

```bash
cd frontend
npx shadcn@latest add select separator avatar dropdown-menu
```

- [ ] **Step 2: Create sidebar component**

A sidebar with navigation links: Dashboard, Performance, Allocation, Transactions, Import, Settings. Includes portfolio selector dropdown at the top and user menu at the bottom.

- [ ] **Step 3: Create app layout**

Wraps authenticated pages. Redirects to `/login` if no user. Shows sidebar + main content area.

- [ ] **Step 4: Create portfolio context**

```typescript
// frontend/src/lib/portfolio-context.tsx
"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { listPortfolios } from "./api/portfolios";
import type { Portfolio } from "@/types/api";

interface PortfolioContextType {
  portfolios: Portfolio[];
  selected: Portfolio | null;
  setSelected: (p: Portfolio) => void;
}

const PortfolioContext = createContext<PortfolioContextType | null>(null);

export function PortfolioProvider({ children }: { children: ReactNode }) {
  const [selected, setSelected] = useState<Portfolio | null>(null);
  const { data } = useQuery({
    queryKey: ["portfolios"],
    queryFn: listPortfolios,
  });

  const portfolios = data?.results ?? [];

  // Auto-select first portfolio (in useEffect to avoid infinite re-renders)
  useEffect(() => {
    if (portfolios.length > 0 && !selected) {
      setSelected(portfolios[0]);
    }
  }, [portfolios, selected]);

  return (
    <PortfolioContext.Provider value={{ portfolios, selected, setSelected }}>
      {children}
    </PortfolioContext.Provider>
  );
}

export function usePortfolio() {
  const ctx = useContext(PortfolioContext);
  if (!ctx) throw new Error("usePortfolio must be used within PortfolioProvider");
  return ctx;
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: add app layout with sidebar navigation and portfolio context"
```

---

## Chunk 6: Frontend Pages

### Task 22: Dashboard Page (Holdings Overview)

**Files:**
- Create: `frontend/src/app/dashboard/page.tsx`

- [ ] **Step 1: Install shadcn table component**

```bash
cd frontend && npx shadcn@latest add table badge
```

- [ ] **Step 2: Create dashboard page**

Uses `usePortfolio()` to get selected portfolio. Queries `/holdings/` and `/summary/` endpoints. Displays:
- Summary cards at top (total value, total gain/loss, return %)
- Table of holdings (instrument name, ticker, quantity, avg buy price, current value, gain/loss with color coding)

- [ ] **Step 3: Verify in browser**

Start with `docker compose up`, navigate to `/dashboard` after login.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/dashboard/
git commit -m "feat: add dashboard page with holdings table and portfolio summary"
```

### Task 23: Transactions Page

**Files:**
- Create: `frontend/src/app/transactions/page.tsx`

- [ ] **Step 1: Create transactions page**

Queries `/portfolios/:id/transactions/`. Displays sortable, filterable table with columns: date, ticker, type (colored badge), quantity, price, fee, total, broker source. Filters: transaction type dropdown, date range picker, search by ticker.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/transactions/
git commit -m "feat: add transactions page with filterable table"
```

### Task 24: Performance Page

**Files:**
- Create: `frontend/src/app/performance/page.tsx`

- [ ] **Step 1: Create performance page**

Queries `/portfolios/:id/performance/?period=X`. Displays:
- Period selector buttons (1W, 1M, 3M, 6M, 1Y, ALL)
- Line chart (Recharts `LineChart` with `ResponsiveContainer`)
- Return % displayed above chart

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/performance/
git commit -m "feat: add performance page with line chart and period selector"
```

### Task 25: Allocation Page

**Files:**
- Create: `frontend/src/app/allocation/page.tsx`

- [ ] **Step 1: Install shadcn tabs**

```bash
cd frontend && npx shadcn@latest add tabs
```

- [ ] **Step 2: Create allocation page**

Queries `/portfolios/:id/allocation/?group_by=X`. Displays:
- Tabs: Sector, Country, Asset Type
- Recharts `PieChart` for Sector and Country tabs
- Recharts `Treemap` for Asset Type tab
- Legend with percentages

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/allocation/
git commit -m "feat: add allocation page with pie charts by sector/country/asset type"
```

### Task 26: Import Page

**Files:**
- Create: `frontend/src/app/import/page.tsx`

- [ ] **Step 1: Create import page**

Two sections:

**CSV Import:**
- Broker selector dropdown (DeGiro initially)
- Drag-and-drop file upload area
- Calls `uploadCsv()`, displays preview table of parsed transactions
- Confirm button calls `confirmImport()`
- Shows result (imported/skipped/warnings)

**Broker Connection (future):**
- Placeholder card with "Coming soon" for API sync

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/import/
git commit -m "feat: add import page with CSV upload, preview, and confirm flow"
```

### Task 27: Settings Page

**Files:**
- Create: `frontend/src/app/settings/page.tsx`

- [ ] **Step 1: Create settings page**

- Base currency selector (EUR, USD, GBP, CHF)
- Change password form
- Both call `updateMe()` API

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/settings/
git commit -m "feat: add settings page with currency and password management"
```

---

## Chunk 7: Testing

### Task 28: Backend Integration Tests

**Files:**
- Create: `backend/apps/tests/__init__.py`
- Create: `backend/apps/tests/test_integration.py`

- [ ] **Step 1: Write integration tests for full import-to-dashboard flow**

```python
# backend/apps/tests/test_integration.py
import pytest
from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.models import User
from apps.instruments.models import Instrument
from apps.portfolios.models import Portfolio, Holding, Transaction
from apps.market_data.providers.base import PriceResult

@pytest.mark.django_db
class TestImportToDashboardFlow:
    """Integration: upload CSV -> confirm import -> view holdings -> view summary"""

    def setup_method(self):
        self.user = User.objects.create_user(username="test", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.portfolio = Portfolio.objects.create(user=self.user, name="Main")

    @patch("apps.instruments.services.yf")
    def test_full_csv_import_and_dashboard(self, mock_yf):
        # Mock yfinance for instrument resolution
        mock_search = MagicMock()
        mock_search.quotes = [{"symbol": "IWDA.AS", "shortname": "iShares MSCI World"}]
        mock_yf.Search.return_value = mock_search
        mock_ticker = MagicMock()
        mock_ticker.info = {"sector": "Diversified", "country": "Ireland", "quoteType": "ETF"}
        mock_yf.Ticker.return_value = mock_ticker

        # Step 1: Upload CSV for preview
        csv_content = (
            "Date,Time,Product,ISIN,Description,FX,Change,,Balance,,Order ID\n"
            "13-01-2025,09:15,MSCI World,IE00B4L5Y983,Buy 10 @ 75.50 EUR,,EUR,-755.00,EUR,1245.00,12345678\n"
        )
        from io import BytesIO
        f = BytesIO(csv_content.encode())
        f.name = "transactions.csv"

        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/",
            {"file": f, "broker": "degiro"},
            format="multipart",
        )
        assert resp.status_code == status.HTTP_200_OK
        preview_id = resp.data["preview_id"]
        assert len(resp.data["transactions"]) == 1

        # Step 2: Confirm import
        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/confirm/",
            {"preview_id": preview_id},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["imported"] == 1

        # Step 3: Verify holdings created
        resp = self.client.get(f"/api/portfolios/{self.portfolio.id}/holdings/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 1
        assert resp.data["results"][0]["quantity"] == "10.000000"

    @patch("apps.instruments.services.yf")
    def test_duplicate_import_skips(self, mock_yf):
        mock_search = MagicMock()
        mock_search.quotes = [{"symbol": "IWDA.AS", "shortname": "Test"}]
        mock_yf.Search.return_value = mock_search
        mock_ticker = MagicMock()
        mock_ticker.info = {"quoteType": "ETF"}
        mock_yf.Ticker.return_value = mock_ticker

        csv_content = (
            "Date,Time,Product,ISIN,Description,FX,Change,,Balance,,Order ID\n"
            "13-01-2025,09:15,MSCI World,IE00B4L5Y983,Buy 10 @ 75.50 EUR,,EUR,-755.00,EUR,1245.00,12345678\n"
        )

        # First import
        from io import BytesIO
        f = BytesIO(csv_content.encode())
        f.name = "transactions.csv"
        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/",
            {"file": f, "broker": "degiro"}, format="multipart",
        )
        preview_id = resp.data["preview_id"]
        self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/confirm/",
            {"preview_id": preview_id},
        )

        # Second import of same CSV
        f2 = BytesIO(csv_content.encode())
        f2.name = "transactions.csv"
        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/",
            {"file": f2, "broker": "degiro"}, format="multipart",
        )
        preview_id2 = resp.data["preview_id"]
        resp = self.client.post(
            f"/api/portfolios/{self.portfolio.id}/import/csv/confirm/",
            {"preview_id": preview_id2},
        )
        assert resp.data["imported"] == 0
        assert resp.data["skipped"] == 1

@pytest.mark.django_db
class TestAuthFlow:
    """Integration: register -> login -> access protected endpoint"""

    def test_register_login_access(self):
        client = APIClient()

        # Register
        resp = client.post("/api/auth/register/", {
            "username": "newuser", "password": "securepass123", "email": "new@example.com",
        })
        assert resp.status_code == status.HTTP_201_CREATED

        # Login
        resp = client.post("/api/auth/login/", {
            "username": "newuser", "password": "securepass123",
        })
        assert resp.status_code == status.HTTP_200_OK
        token = resp.data["access"]

        # Access protected endpoint
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = client.get("/api/user/me/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["username"] == "newuser"

    def test_unauthenticated_access_denied(self):
        client = APIClient()
        resp = client.get("/api/portfolios/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
class TestPortfolioIsolation:
    """Integration: users cannot see each other's data"""

    def test_user_cannot_see_other_portfolios(self):
        user1 = User.objects.create_user(username="user1", password="pass12345")
        user2 = User.objects.create_user(username="user2", password="pass12345")
        Portfolio.objects.create(user=user1, name="User1 Portfolio")
        Portfolio.objects.create(user=user2, name="User2 Portfolio")

        client = APIClient()
        client.force_authenticate(user=user1)
        resp = client.get("/api/portfolios/")
        names = [p["name"] for p in resp.data["results"]]
        assert "User1 Portfolio" in names
        assert "User2 Portfolio" not in names
```

- [ ] **Step 2: Run integration tests**

```bash
cd backend && python -m pytest apps/tests/test_integration.py -v
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/apps/tests/
git commit -m "test: add backend integration tests for import flow, auth, and data isolation"
```

### Task 29: Frontend Unit Tests Setup

**Files:**
- Modify: `frontend/package.json` (add test deps)
- Create: `frontend/jest.config.ts`
- Create: `frontend/src/lib/api/__tests__/client.test.ts`
- Create: `frontend/src/lib/__tests__/auth-context.test.tsx`

- [ ] **Step 1: Install testing dependencies**

```bash
cd frontend && npm install -D jest @testing-library/react @testing-library/jest-dom @testing-library/user-event @types/jest ts-jest jest-environment-jsdom
```

- [ ] **Step 2: Create jest.config.ts**

```typescript
// frontend/jest.config.ts
import type { Config } from "jest";

const config: Config = {
  testEnvironment: "jsdom",
  transform: {
    "^.+\\.tsx?$": ["ts-jest", { tsconfig: "tsconfig.json" }],
  },
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
  },
  setupFilesAfterSetup: ["@testing-library/jest-dom"],
};

export default config;
```

- [ ] **Step 3: Write API client unit tests**

```typescript
// frontend/src/lib/api/__tests__/client.test.ts
import { apiClient, ApiError } from "../client";

describe("apiClient", () => {
  beforeEach(() => {
    global.fetch = jest.fn();
    localStorage.clear();
  });

  it("makes GET request with auth token", async () => {
    localStorage.setItem("access_token", "test-token");
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ data: "test" }),
    });

    const result = await apiClient("/test/");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/test/"),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer test-token",
        }),
      }),
    );
    expect(result).toEqual({ data: "test" });
  });

  it("throws ApiError on non-ok response", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Unauthorized" }),
    });

    await expect(apiClient("/test/")).rejects.toThrow(ApiError);
  });

  it("makes POST with JSON body", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      status: 201,
      json: () => Promise.resolve({ id: 1 }),
    });

    await apiClient("/test/", { method: "POST", body: { name: "test" } });
    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "test" }),
      }),
    );
  });
});
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx jest --verbose
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/jest.config.ts frontend/package.json frontend/src/lib/api/__tests__/
git commit -m "test: add frontend testing setup and API client unit tests"
```

### Task 30: Frontend Component Tests

**Files:**
- Create: `frontend/src/app/(auth)/__tests__/login.test.tsx`
- Create: `frontend/src/app/dashboard/__tests__/page.test.tsx`

- [ ] **Step 1: Write login page test**

```typescript
// frontend/src/app/(auth)/__tests__/login.test.tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import LoginPage from "../login/page";

// Mock next/navigation
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

// Mock auth context
const mockRefreshUser = jest.fn();
jest.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ refreshUser: mockRefreshUser }),
}));

// Mock auth API
jest.mock("@/lib/api/auth", () => ({
  login: jest.fn(),
}));

describe("LoginPage", () => {
  it("renders login form", () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <LoginPage />
      </QueryClientProvider>,
    );
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /login/i })).toBeInTheDocument();
  });

  it("shows error on failed login", async () => {
    const { login } = require("@/lib/api/auth");
    login.mockRejectedValue(new Error("Invalid"));

    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <LoginPage />
      </QueryClientProvider>,
    );

    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: "user" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: /login/i }));

    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Write dashboard page test**

```typescript
// frontend/src/app/dashboard/__tests__/page.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock portfolio context
jest.mock("@/lib/portfolio-context", () => ({
  usePortfolio: () => ({
    selected: { id: 1, name: "Main" },
    portfolios: [{ id: 1, name: "Main" }],
    setSelected: jest.fn(),
  }),
}));

// Mock API
jest.mock("@/lib/api/portfolios", () => ({
  getHoldings: jest.fn().mockResolvedValue({
    results: [
      {
        id: 1,
        instrument: { ticker: "IWDA.AS", name: "MSCI World", asset_type: "ETF" },
        quantity: "10.000000",
        avg_buy_price: "75.500000",
      },
    ],
  }),
  getSummary: jest.fn().mockResolvedValue({
    total_value: "800.00",
    total_cost: "755.00",
    total_gain_loss: "45.00",
    total_return_pct: "5.96",
  }),
}));

import DashboardPage from "../page";

describe("DashboardPage", () => {
  it("renders holdings table with data", async () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <DashboardPage />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("IWDA.AS")).toBeInTheDocument();
      expect(screen.getByText("MSCI World")).toBeInTheDocument();
    });
  });

  it("shows portfolio summary", async () => {
    const qc = new QueryClient();
    render(
      <QueryClientProvider client={qc}>
        <DashboardPage />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText(/800\.00/)).toBeInTheDocument();
      expect(screen.getByText(/45\.00/)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 3: Run all frontend tests**

```bash
cd frontend && npx jest --verbose
```

Expected: PASS.

- [ ] **Step 4: Add test script to package.json**

Ensure `"test": "jest"` is in the `scripts` section of `frontend/package.json`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/
git commit -m "test: add frontend component tests for login and dashboard"
```

### Task 31: Backend Test Suite Verification

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && python -m pytest -v --tb=short
```

Expected: all tests PASS.

- [ ] **Step 2: Run all frontend tests**

```bash
cd frontend && npm test
```

Expected: all tests PASS.

- [ ] **Step 3: Fix any failures**

---

## Chunk 8: Integration & Polish

### Task 32: Docker Compose End-to-End Verification

- [ ] **Step 1: Full rebuild and start**

```bash
docker compose down -v && docker compose build && docker compose up -d
```

- [ ] **Step 2: Run Django migrations**

```bash
docker compose exec backend python manage.py migrate
```

- [ ] **Step 3: Manual smoke test**

1. Register via UI at `http://localhost:3000/register`
2. Login
3. Create a portfolio
4. Import a DeGiro CSV
5. Verify dashboard shows holdings
6. Check performance, allocation, transactions pages
7. Change currency in settings

- [ ] **Step 4: Commit any fixes**

```bash
git add -A && git commit -m "fix: integration fixes from end-to-end testing"
```

### Task 33: CLAUDE.md

- [ ] **Step 1: Create CLAUDE.md**

Document the project structure, development commands, and architecture for future Claude Code sessions.

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add CLAUDE.md for Claude Code guidance"
```
