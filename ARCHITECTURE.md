# Trending YouTube Livestreams - Architecture Design

## 1. Architecture Diagram (Text-Based)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Docker Network: streamrank_net                      │
│                                                                                  │
│  ┌──────────────┐     ┌──────────────────────────────────────────────────────┐  │
│  │              │     │                   API Container                       │  │
│  │    MySQL     │◄────┤  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │  │
│  │  Container   │     │  │   FastAPI   │  │   Redis     │  │     JWT      │  │  │
│  │              │     │  │   Router    │  │   Cache     │  │  Auth Layer  │  │  │
│  │  Port: 3306  │     │  └──────┬──────┘  └──────┬──────┘  └──────────────┘  │  │
│  │              │     │         │                │                            │  │
│  │  - streams   │     │  ┌──────▼────────────────▼──────┐                    │  │
│  │  - viewership│     │  │      Service Layer           │                    │  │
│  │  - users     │     │  │  - StreamService             │                    │  │
│  │              │     │  │  - RankingService            │                    │  │
│  └──────▲───────┘     │  │  - AnomalyDetectionService   │                    │  │
│         │             │  └──────────────────────────────┘                    │  │
│         │             │                                          Port: 8000  │  │
│         │             └──────────────────────────────────────────────────────┘  │
│         │                                                                        │
│         │             ┌──────────────────────────────────────────────────────┐  │
│         │             │                 Worker Container                      │  │
│         └─────────────┤  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │  │
│                       │  │  Scheduler  │  │  YouTube    │  │    Data      │  │  │
│                       │  │  (APScheduler)│ │  API Client │  │   Cleanup    │  │  │
│                       │  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  │  │
│                       │         │                │                │          │  │
│                       │  ┌──────▼────────────────▼────────────────▼───────┐  │  │
│                       │  │              Task Handlers                      │  │  │
│                       │  │  - poll_livestreams (every 2 min)              │  │  │
│                       │  │  - cleanup_old_data (daily at 3 AM)            │  │  │
│                       │  └────────────────────────────────────────────────┘  │  │
│                       └──────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────┐
                    │           External Services              │
                    │  ┌─────────────┐    ┌────────────────┐  │
                    │  │  YouTube    │    │   CDN/Static   │  │
                    │  │  Data API   │    │    Hosting     │  │
                    │  └─────────────┘    └────────────────┘  │
                    └─────────────────────────────────────────┘

┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│      Frontend Widget            │    │       Frontend Admin            │
│   (Embeddable Component)        │    │     (Management UI)             │
│                                 │    │                                 │
│  - Static build (dist/)         │    │  - React + TypeScript           │
│  - <script> tag embed           │    │  - JWT authenticated            │
│  - Polls /api/v1/rankings       │    │  - Stream management            │
│  - Minimal dependencies         │    │  - Analytics dashboard          │
│                                 │    │  - Anomaly configuration        │
│  Port: N/A (static files)       │    │  Port: 5173 (dev)               │
└─────────────────────────────────┘    └─────────────────────────────────┘
```

---

## 2. Data Flow Description

### 2.1 Viewership Data Collection Flow

```
YouTube Data API
      │
      ▼ (every 2 minutes)
┌─────────────────┐
│  Worker:        │
│  poll_livestreams│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  1. Fetch active scientific livestreams             │
│  2. For each stream:                                │
│     a. Get current viewer count                     │
│     b. Insert into viewership_snapshots table       │
│     c. Update streams.current_viewers               │
│     d. Trigger anomaly detection                    │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Anomaly Detection (Strategy Pattern)               │
│  ┌───────────────┐  ┌───────────────┐               │
│  │ Quantile      │  │ Z-Score       │               │
│  │ Strategy      │  │ Strategy      │               │
│  └───────────────┘  └───────────────┘               │
│                                                     │
│  All strategies use logistic normalization to       │
│  map raw scores to 0-100 scale (sigmoid function)   │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  If anomaly:    │
│  Insert into    │
│  anomaly_events │
└─────────────────┘
```

### 2.2 Ranking Request Flow

```
Client (Widget/Admin)
      │
      │ GET /api/v1/rankings?category=science&limit=10
      ▼
┌─────────────────┐
│  API Gateway    │
│  (FastAPI)      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Cache Check (Redis)                                │
│  Key: rankings:science:10                           │
│  TTL: 5 minutes                                     │
└────────┬────────────────────────┬───────────────────┘
         │                        │
    Cache HIT                Cache MISS
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌─────────────────────────────┐
│  Return cached  │    │  Query MySQL:               │
│  response       │    │  - Join streams + latest    │
│                 │    │    viewership               │
│                 │    │  - Calculate trend score    │
│                 │    │  - Sort by composite rank   │
│                 │    │  - Cache result             │
└─────────────────┘    └─────────────────────────────┘
```

### 2.3 Admin Authentication Flow

```
Admin User
      │
      │ POST /api/v1/auth/login {email, password}
      ▼
┌─────────────────────────────────────────────────────┐
│  1. Validate credentials against users table        │
│  2. Verify password hash (bcrypt)                   │
│  3. Generate JWT token (HS256, 24h expiry)          │
│  4. Return {access_token, token_type}               │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Subsequent requests:                               │
│  Authorization: Bearer <token>                      │
│  → JWT middleware validates signature + expiry      │
│  → Extracts user_id, injects into request state     │
└─────────────────────────────────────────────────────┘
```

---

## 3. Component Responsibilities

### 3.1 MySQL Container

| Responsibility | Details |
|---------------|---------|
| **Primary data store** | Persistent storage for all application data |
| **Schema management** | Alembic migrations applied on API startup |
| **Data retention** | Worker handles 30-day cleanup |
| **Indexing** | Optimized indexes for time-range queries |

**Tables:**
- `streams` - YouTube livestream metadata
- `viewership_snapshots` - Time-series viewer counts
- `anomaly_events` - Detected viewership spikes
- `users` - Admin user accounts
- `categories` - Scientific topic categories

### 3.2 API Container (FastAPI)

| Responsibility | Details |
|---------------|---------|
| **REST API** | All HTTP endpoints for clients |
| **Authentication** | JWT token generation and validation |
| **Caching** | Redis-based response caching |
| **Validation** | Pydantic request/response models |
| **Rate limiting** | Per-IP and per-user limits |

**Key Modules:**
- `routers/` - Endpoint definitions
- `services/` - Business logic
- `models/` - SQLAlchemy ORM models
- `schemas/` - Pydantic validation schemas
- `core/` - Config, security, dependencies

### 3.3 Worker Container

| Responsibility | Details |
|---------------|---------|
| **YouTube polling** | Fetch livestream data every 2 minutes |
| **Anomaly detection** | Run detection strategies on new data |
| **Data cleanup** | Delete records older than 30 days |
| **Health monitoring** | Self-report status to API |

**Scheduled Tasks:**
| Task | Schedule | Description |
|------|----------|-------------|
| `poll_livestreams` | Every 2 min | Fetch viewer counts |
| `cleanup_old_data` | Daily 3 AM UTC | Delete old snapshots |
| `refresh_stream_metadata` | Every 6 hours | Update titles, thumbnails |

### 3.4 Frontend Widget

| Responsibility | Details |
|---------------|---------|
| **Embeddable display** | Single `<script>` tag integration |
| **Real-time updates** | Poll rankings every 60 seconds |
| **Minimal footprint** | < 50KB gzipped bundle |
| **Customizable** | CSS variables for theming |

**Embed Example:**
```html
<div id="streamrank-widget" data-category="science" data-limit="5"></div>
<script src="https://cdn.example.com/streamrank-widget.js"></script>
```

### 3.5 Frontend Admin

| Responsibility | Details |
|---------------|---------|
| **Stream management** | Add/edit/remove tracked streams |
| **Analytics dashboard** | Viewership charts, trends |
| **Anomaly configuration** | Set thresholds, enable strategies |
| **User management** | Admin account CRUD |

---

## 4. API Contract Summary

### 4.1 Public Endpoints (No Auth)

```yaml
GET /api/v1/rankings
  Query Parameters:
    - category: string (optional) - Filter by category slug
    - limit: int (default: 10, max: 50)
    - include_anomalies: bool (default: false)
  Response: 200 OK
    {
      "data": [
        {
          "stream_id": "abc123",
          "youtube_id": "dQw4w9WgXcQ",
          "title": "Live: Mars Rover Operations",
          "channel_name": "NASA",
          "thumbnail_url": "https://...",
          "current_viewers": 45230,
          "peak_viewers_24h": 67000,
          "trend_score": 0.85,
          "rank": 1,
          "is_anomaly": false,
          "category": "space"
        }
      ],
      "cached_at": "2026-01-25T10:30:00Z",
      "cache_ttl_seconds": 300
    }

GET /api/v1/streams/{youtube_id}
  Response: 200 OK
    {
      "stream_id": "abc123",
      "youtube_id": "dQw4w9WgXcQ",
      "title": "Live: Mars Rover Operations",
      "description": "...",
      "channel_id": "UCLA_DiR1FfKNvjuUpBHmylQ",
      "channel_name": "NASA",
      "thumbnail_url": "https://...",
      "category": "space",
      "current_viewers": 45230,
      "stream_started_at": "2026-01-25T08:00:00Z",
      "is_live": true
    }

GET /api/v1/streams/{youtube_id}/viewership
  Query Parameters:
    - hours: int (default: 24, max: 168)
    - resolution: string (default: "5min", options: "1min", "5min", "15min", "1hour")
  Response: 200 OK
    {
      "youtube_id": "dQw4w9WgXcQ",
      "datapoints": [
        {"timestamp": "2026-01-25T10:00:00Z", "viewers": 42000},
        {"timestamp": "2026-01-25T10:05:00Z", "viewers": 43500}
      ]
    }

GET /api/v1/categories
  Response: 200 OK
    {
      "categories": [
        {"slug": "space", "name": "Space & Astronomy", "stream_count": 12},
        {"slug": "biology", "name": "Biology & Life Sciences", "stream_count": 8}
      ]
    }

GET /health
  Response: 200 OK
    {"status": "healthy", "database": "connected", "cache": "connected"}
```

### 4.2 Admin Endpoints (JWT Required)

```yaml
POST /api/v1/auth/login
  Request Body:
    {"email": "admin@example.com", "password": "secret"}
  Response: 200 OK
    {"access_token": "eyJ...", "token_type": "bearer", "expires_in": 86400}

POST /api/v1/auth/refresh
  Headers: Authorization: Bearer <token>
  Response: 200 OK
    {"access_token": "eyJ...", "token_type": "bearer", "expires_in": 86400}

GET /api/v1/admin/streams
  Headers: Authorization: Bearer <token>
  Query Parameters:
    - page: int (default: 1)
    - per_page: int (default: 20)
    - status: string (optional) - "active", "inactive", "all"
  Response: 200 OK
    {
      "data": [...],
      "pagination": {"page": 1, "per_page": 20, "total": 45}
    }

POST /api/v1/admin/streams
  Headers: Authorization: Bearer <token>
  Request Body:
    {
      "youtube_id": "dQw4w9WgXcQ",
      "category_slug": "space",
      "is_active": true
    }
  Response: 201 Created

PATCH /api/v1/admin/streams/{stream_id}
  Headers: Authorization: Bearer <token>
  Request Body:
    {"category_slug": "physics", "is_active": false}
  Response: 200 OK

DELETE /api/v1/admin/streams/{stream_id}
  Headers: Authorization: Bearer <token>
  Response: 204 No Content

GET /api/v1/admin/anomalies
  Headers: Authorization: Bearer <token>
  Query Parameters:
    - start_date: ISO8601 (optional)
    - end_date: ISO8601 (optional)
    - stream_id: string (optional)
  Response: 200 OK
    {
      "data": [
        {
          "id": "evt_123",
          "stream_id": "abc123",
          "detected_at": "2026-01-25T09:15:00Z",
          "strategy": "zscore",
          "baseline_viewers": 10000,
          "spike_viewers": 45000,
          "deviation_score": 3.5
        }
      ]
    }

GET /api/v1/admin/anomaly-config
  Headers: Authorization: Bearer <token>
  Response: 200 OK
    {
      "strategies": [
        {
          "name": "zscore",
          "enabled": true,
          "threshold": 2.5,
          "lookback_minutes": 60
        },
        {
          "name": "percent_change",
          "enabled": true,
          "threshold": 200,
          "lookback_minutes": 30
        }
      ]
    }

PUT /api/v1/admin/anomaly-config
  Headers: Authorization: Bearer <token>
  Request Body:
    {
      "strategies": [
        {"name": "zscore", "enabled": true, "threshold": 3.0}
      ]
    }
  Response: 200 OK

GET /api/v1/admin/stats
  Headers: Authorization: Bearer <token>
  Response: 200 OK
    {
      "total_streams": 45,
      "active_streams": 12,
      "total_snapshots": 1250000,
      "anomalies_24h": 3,
      "api_requests_24h": 15000,
      "oldest_data": "2025-12-26T00:00:00Z"
    }
```

### 4.3 Error Response Format

```yaml
4xx/5xx Response:
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid request parameters",
      "details": [
        {"field": "limit", "message": "Must be between 1 and 50"}
      ]
    }
  }

Error Codes:
  - VALIDATION_ERROR (400)
  - UNAUTHORIZED (401)
  - FORBIDDEN (403)
  - NOT_FOUND (404)
  - RATE_LIMITED (429)
  - INTERNAL_ERROR (500)
  - YOUTUBE_API_ERROR (502)
```

---

## 5. Technology Stack Decisions

### 5.1 Backend

| Technology | Version | Justification |
|-----------|---------|---------------|
| **Python** | 3.11+ | Excellent async support, rich data science ecosystem |
| **FastAPI** | 0.109+ | High performance, automatic OpenAPI docs, native async |
| **SQLAlchemy** | 2.0+ | Modern async ORM, type hints, migration support |
| **Alembic** | 1.13+ | Database migration management, version control |
| **Pydantic** | 2.0+ | Fast validation, seamless FastAPI integration |
| **APScheduler** | 3.10+ | Robust job scheduling, persistence support |
| **Redis** | 7.0+ | Sub-millisecond caching, atomic operations |
| **PyJWT** | 2.8+ | Standard JWT implementation, minimal dependencies |
| **httpx** | 0.26+ | Modern async HTTP client for YouTube API |
| **bcrypt** | 4.1+ | Industry-standard password hashing |

### 5.2 Database

| Technology | Version | Justification |
|-----------|---------|---------------|
| **MySQL** | 8.0+ | Mature, excellent time-series query performance with proper indexing |
| **Redis** | 7.0+ | In-memory caching, TTL support, atomic operations |

**Why MySQL over PostgreSQL?**
- Requirement specified MySQL
- Excellent performance for time-range queries with proper indexing
- Wide hosting support

**Why Redis for caching?**
- Sub-millisecond latency
- Native TTL support
- Atomic operations for cache invalidation
- Can be embedded in API container for simplicity

### 5.3 Frontend

| Technology | Version | Justification |
|-----------|---------|---------------|
| **React** | 18+ | Component model, large ecosystem |
| **TypeScript** | 5.0+ | Type safety, better DX, fewer runtime errors |
| **Vite** | 5.0+ | Fast builds, excellent DX, native ESM |
| **TanStack Query** | 5.0+ | Powerful data fetching, caching, sync |
| **Recharts** | 2.10+ | Lightweight, composable React charts |
| **Tailwind CSS** | 3.4+ | Rapid styling, small bundle with purge |

**Widget-specific:**
| Technology | Justification |
|-----------|---------------|
| **Preact** | 3KB alternative to React for minimal bundle |
| **Vanilla Extract** | Zero-runtime CSS for isolation |

### 5.4 Infrastructure

| Technology | Version | Justification |
|-----------|---------|---------------|
| **Docker** | 24+ | Consistent environments, easy deployment |
| **Docker Compose** | 2.24+ | Multi-container orchestration for dev/prod |
| **Nginx** | 1.25+ | Reverse proxy, static file serving, SSL termination |

---

## 6. Directory Structure

```
stream_rank/
├── docker-compose.yml              # Development orchestration
├── docker-compose.prod.yml         # Production overrides
├── .env.example                    # Environment template
├── .gitignore
├── README.md
├── ARCHITECTURE.md                 # This document
│
├── backend/
│   ├── Dockerfile
│   ├── Dockerfile.worker
│   ├── pyproject.toml              # Python dependencies (Poetry/uv)
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application factory
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py           # Settings (pydantic-settings)
│   │   │   ├── database.py         # Async SQLAlchemy setup
│   │   │   ├── redis.py            # Redis connection
│   │   │   ├── security.py         # JWT, password hashing
│   │   │   └── dependencies.py     # FastAPI dependencies
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── stream.py           # Stream ORM model
│   │   │   ├── viewership.py       # ViewershipSnapshot model
│   │   │   ├── anomaly.py          # AnomalyEvent model
│   │   │   ├── user.py             # User model
│   │   │   └── category.py         # Category model
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── stream.py           # Stream Pydantic schemas
│   │   │   ├── ranking.py          # Ranking response schemas
│   │   │   ├── anomaly.py          # Anomaly schemas
│   │   │   ├── auth.py             # Auth request/response
│   │   │   └── common.py           # Pagination, errors
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── stream_service.py   # Stream CRUD operations
│   │   │   ├── ranking_service.py  # Ranking calculations
│   │   │   ├── youtube_service.py  # YouTube API client
│   │   │   └── anomaly/
│   │   │       ├── __init__.py
│   │   │       ├── detector.py     # AnomalyDetector (context)
│   │   │       ├── base.py         # AnomalyStrategy (interface)
│   │   │       ├── zscore.py       # Z-Score implementation
│   │   │       ├── percent_change.py
│   │   │       └── moving_average.py
│   │   │
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── rankings.py         # GET /rankings
│   │   │   ├── streams.py          # GET /streams/*
│   │   │   ├── categories.py       # GET /categories
│   │   │   ├── auth.py             # POST /auth/*
│   │   │   ├── admin/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── streams.py      # Admin stream management
│   │   │   │   ├── anomalies.py    # Anomaly config & history
│   │   │   │   └── stats.py        # Dashboard stats
│   │   │   └── health.py           # Health check
│   │   │
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── rate_limit.py
│   │       └── logging.py
│   │
│   ├── worker/
│   │   ├── __init__.py
│   │   ├── main.py                 # Worker entry point
│   │   ├── scheduler.py            # APScheduler setup
│   │   └── tasks/
│   │       ├── __init__.py
│   │       ├── poll_livestreams.py
│   │       ├── cleanup_data.py
│   │       └── refresh_metadata.py
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py             # Pytest fixtures
│       ├── test_rankings.py
│       ├── test_anomaly_detection.py
│       └── test_auth.py
│
├── frontend/
│   ├── admin/
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── vite.config.ts
│   │   ├── index.html
│   │   ├── src/
│   │   │   ├── main.tsx
│   │   │   ├── App.tsx
│   │   │   ├── api/
│   │   │   │   ├── client.ts       # Axios/fetch wrapper
│   │   │   │   ├── streams.ts
│   │   │   │   ├── rankings.ts
│   │   │   │   └── auth.ts
│   │   │   ├── components/
│   │   │   │   ├── Layout/
│   │   │   │   ├── StreamTable/
│   │   │   │   ├── ViewershipChart/
│   │   │   │   └── AnomalyBadge/
│   │   │   ├── pages/
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── Streams.tsx
│   │   │   │   ├── StreamDetail.tsx
│   │   │   │   ├── Anomalies.tsx
│   │   │   │   ├── Settings.tsx
│   │   │   │   └── Login.tsx
│   │   │   ├── hooks/
│   │   │   │   ├── useAuth.ts
│   │   │   │   ├── useStreams.ts
│   │   │   │   └── useRankings.ts
│   │   │   ├── context/
│   │   │   │   └── AuthContext.tsx
│   │   │   └── types/
│   │   │       └── index.ts
│   │   └── public/
│   │
│   └── widget/
│       ├── Dockerfile
│       ├── package.json
│       ├── tsconfig.json
│       ├── vite.config.ts
│       ├── src/
│       │   ├── main.ts             # Widget entry point
│       │   ├── StreamRankWidget.tsx
│       │   ├── components/
│       │   │   ├── RankingList.tsx
│       │   │   └── StreamCard.tsx
│       │   ├── api/
│       │   │   └── rankings.ts
│       │   └── styles/
│       │       └── widget.css
│       └── dist/                   # Built widget files
│           ├── streamrank-widget.js
│           └── streamrank-widget.css
│
├── nginx/
│   ├── nginx.conf
│   └── conf.d/
│       └── default.conf
│
└── scripts/
    ├── init-db.sh                  # Database initialization
    ├── seed-data.py                # Development seed data
    └── backup-db.sh                # Database backup script
```

---

## 7. Database Schema

```sql
-- Categories for scientific topics
CREATE TABLE categories (
    id VARCHAR(36) PRIMARY KEY,
    slug VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tracked YouTube livestreams
CREATE TABLE streams (
    id VARCHAR(36) PRIMARY KEY,
    youtube_id VARCHAR(20) UNIQUE NOT NULL,
    channel_id VARCHAR(30) NOT NULL,
    channel_name VARCHAR(100) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    thumbnail_url VARCHAR(500),
    category_id VARCHAR(36) REFERENCES categories(id),
    is_active BOOLEAN DEFAULT TRUE,
    is_live BOOLEAN DEFAULT FALSE,
    current_viewers INT DEFAULT 0,
    peak_viewers INT DEFAULT 0,
    stream_started_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_youtube_id (youtube_id),
    INDEX idx_category (category_id),
    INDEX idx_is_live (is_live),
    INDEX idx_current_viewers (current_viewers DESC)
);

-- Time-series viewership data
CREATE TABLE viewership_snapshots (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stream_id VARCHAR(36) NOT NULL REFERENCES streams(id) ON DELETE CASCADE,
    viewer_count INT NOT NULL,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_stream_time (stream_id, recorded_at DESC),
    INDEX idx_recorded_at (recorded_at)
) PARTITION BY RANGE (UNIX_TIMESTAMP(recorded_at)) (
    -- Partitions created dynamically for 30-day rolling window
);

-- Detected anomaly events
CREATE TABLE anomaly_events (
    id VARCHAR(36) PRIMARY KEY,
    stream_id VARCHAR(36) NOT NULL REFERENCES streams(id) ON DELETE CASCADE,
    strategy VARCHAR(50) NOT NULL,
    baseline_viewers INT NOT NULL,
    spike_viewers INT NOT NULL,
    deviation_score DECIMAL(10,4) NOT NULL,
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    
    INDEX idx_stream_detected (stream_id, detected_at DESC),
    INDEX idx_detected_at (detected_at)
);

-- Admin users
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- Anomaly detection configuration
CREATE TABLE anomaly_config (
    id VARCHAR(36) PRIMARY KEY,
    strategy VARCHAR(50) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    threshold DECIMAL(10,4) NOT NULL,
    lookback_minutes INT NOT NULL DEFAULT 60,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

---

## 8. Anomaly Detection Strategy Pattern

```python
# backend/app/services/anomaly/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

@dataclass
class ViewershipDataPoint:
    timestamp: datetime
    viewer_count: int

@dataclass
class AnomalyResult:
    is_anomaly: bool
    strategy_name: str
    baseline_value: float
    current_value: int
    deviation_score: float
    metadata: dict

class AnomalyStrategy(ABC):
    """Base class for anomaly detection strategies."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this strategy."""
        pass
    
    @abstractmethod
    def detect(
        self,
        current_viewers: int,
        historical_data: List[ViewershipDataPoint],
        threshold: float
    ) -> AnomalyResult:
        """
        Analyze viewership data and detect anomalies.
        
        Args:
            current_viewers: Latest viewer count
            historical_data: Recent viewership history
            threshold: Strategy-specific threshold
            
        Returns:
            AnomalyResult with detection outcome
        """
        pass


# backend/app/services/anomaly/detector.py
class AnomalyDetector:
    """Context class that uses strategies to detect anomalies."""
    
    def __init__(self):
        self._strategies: Dict[str, AnomalyStrategy] = {}
    
    def register_strategy(self, strategy: AnomalyStrategy) -> None:
        self._strategies[strategy.name] = strategy
    
    async def detect_anomalies(
        self,
        stream_id: str,
        current_viewers: int,
        db: AsyncSession
    ) -> List[AnomalyResult]:
        """Run all enabled strategies and return results."""
        results = []
        
        # Fetch enabled strategies from config
        configs = await self._get_enabled_configs(db)
        
        for config in configs:
            strategy = self._strategies.get(config.strategy)
            if not strategy:
                continue
                
            # Fetch historical data for lookback period
            historical = await self._get_historical_data(
                db, stream_id, config.lookback_minutes
            )
            
            result = strategy.detect(
                current_viewers, historical, config.threshold
            )
            
            if result.is_anomaly:
                results.append(result)
        
        return results
```

---

## 9. Caching Strategy

```python
# backend/app/services/ranking_service.py
from app.core.redis import redis_client

RANKINGS_CACHE_TTL = 300  # 5 minutes

async def get_cached_rankings(
    category: Optional[str],
    limit: int
) -> Optional[RankingResponse]:
    """Try to get rankings from cache."""
    cache_key = f"rankings:{category or 'all'}:{limit}"
    
    cached = await redis_client.get(cache_key)
    if cached:
        return RankingResponse.model_validate_json(cached)
    return None

async def cache_rankings(
    category: Optional[str],
    limit: int,
    response: RankingResponse
) -> None:
    """Store rankings in cache."""
    cache_key = f"rankings:{category or 'all'}:{limit}"
    
    await redis_client.setex(
        cache_key,
        RANKINGS_CACHE_TTL,
        response.model_dump_json()
    )

async def invalidate_rankings_cache() -> None:
    """Invalidate all ranking caches (called after viewership updates)."""
    keys = await redis_client.keys("rankings:*")
    if keys:
        await redis_client.delete(*keys)
```

---

## 10. Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: streamrank_mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: streamrank
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./scripts/init-db.sh:/docker-entrypoint-initdb.d/init-db.sh
    ports:
      - "3306:3306"
    networks:
      - streamrank_net
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: streamrank_redis
    ports:
      - "6379:6379"
    networks:
      - streamrank_net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: streamrank_api
    environment:
      DATABASE_URL: mysql+aiomysql://${MYSQL_USER}:${MYSQL_PASSWORD}@mysql:3306/streamrank
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET: ${JWT_SECRET}
      YOUTUBE_API_KEY: ${YOUTUBE_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - streamrank_net
    volumes:
      - ./backend:/app  # Dev only
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.worker
    container_name: streamrank_worker
    environment:
      DATABASE_URL: mysql+aiomysql://${MYSQL_USER}:${MYSQL_PASSWORD}@mysql:3306/streamrank
      REDIS_URL: redis://redis:6379/0
      YOUTUBE_API_KEY: ${YOUTUBE_API_KEY}
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - streamrank_net
    volumes:
      - ./backend:/app  # Dev only

  admin:
    build:
      context: ./frontend/admin
      dockerfile: Dockerfile
    container_name: streamrank_admin
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://localhost:8000
    volumes:
      - ./frontend/admin:/app
      - /app/node_modules
    networks:
      - streamrank_net
    command: npm run dev -- --host

networks:
  streamrank_net:
    driver: bridge

volumes:
  mysql_data:
```

---

## 11. Security Considerations

| Area | Implementation |
|------|----------------|
| **Authentication** | JWT tokens with 24h expiry, refresh token rotation |
| **Password storage** | bcrypt with cost factor 12 |
| **API rate limiting** | 100 req/min public, 1000 req/min authenticated |
| **CORS** | Whitelist specific origins in production |
| **SQL injection** | SQLAlchemy ORM with parameterized queries |
| **Input validation** | Pydantic models validate all inputs |
| **Secrets** | Environment variables, never in code |
| **HTTPS** | Nginx SSL termination in production |

---

## 12. Monitoring & Observability

| Component | Tool | Purpose |
|-----------|------|---------|
| **API metrics** | Prometheus + FastAPI instrumentation | Request latency, error rates |
| **Logs** | Structured JSON logging → stdout | Centralized log aggregation |
| **Health checks** | `/health` endpoint | Container orchestration |
| **Database** | MySQL slow query log | Query optimization |
| **Alerts** | Configurable thresholds | Anomaly detection failures |

---

*This architecture document serves as the implementation guide. Each component should be built following these specifications.*
