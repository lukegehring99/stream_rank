# StreamRank - Trending YouTube Livestreams Tracker

A production-ready web application for tracking **trending scientific YouTube livestreams** based on anomalous increases in live viewership. Perfect for monitoring volcano eruptions, space events, and other scientific phenomena that cause sudden viewer spikes.

![Architecture](https://img.shields.io/badge/architecture-microservices-blue)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/frontend-React%20TypeScript-61DAFB)
![Database](https://img.shields.io/badge/database-MySQL-4479A1)
![Docker](https://img.shields.io/badge/docker-compose-2496ED)

## 🎯 Features

- **Real-time Trending Detection**: Automatically detects livestreams with anomalous viewership spikes
- **Multiple Anomaly Algorithms**: Pluggable strategy pattern with Quantile-based and Z-score algorithms
- **Embeddable Widget**: Static React widget for embedding on external sites (GitHub Pages compatible)
- **Admin Dashboard**: Full CRUD management with JWT authentication
- **Automatic Data Retention**: 30-day rolling window with automatic cleanup
- **Cached Rankings**: 5-minute TTL cache for efficient API responses
- **Docker Ready**: Complete docker-compose setup for local development and production

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Docker Network: streamrank_net              │
│                                                                 │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │  MySQL   │  │   FastAPI    │  │   Worker     │               │
│  │   DB     │◄─┤   API        │  │  (Scheduler) │               │
│  │          │  │              │  │              │               │
│  │ :3306    │  │   :8000      │  │              │               │
│  └──────────┘  └──────────────┘  └──────────────┘               │
│                                          │                      │
│                                          ▼                      │
│                              ┌──────────────────┐               │
│                              │  YouTube API v3  │               │
│                              └──────────────────┘               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────┐     ┌─────────────────────┐
│   Widget (React)    │     │   Admin (React)     │
│   Embeddable        │     │   Dashboard         │
│   Static Build      │     │   :3001             │
└─────────────────────┘     └─────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- YouTube Data API key ([Get one here](https://console.cloud.google.com/apis/library/youtube.googleapis.com))

### 1. Clone and Configure

```bash
git clone <repository-url>
cd stream_rank

# Copy environment file
cp .env.example .env

# Edit .env with your settings
# IMPORTANT: Set YOUTUBE_API_KEY and JWT_SECRET
```

### 2. Start Services

```bash
# Production (mysql + api + worker only)
docker compose -f docker-compose.yml up --build -d

# Include Admin UI + Widget (uses override file)
docker compose -f docker-compose.yml -f docker-compose.override.yml up --build -d

# View logs
docker compose logs -f
```

### 3. Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | Swagger documentation |
| Admin UI | http://localhost:3001 | Admin dashboard |
| Widget | http://localhost:3000 | Embeddable widget |

### 4. Default Admin Login

```
Username: admin
Password: admin123
```

> ⚠️ **Change this password in production!**

## 📁 Project Structure

```
stream_rank/
├── app/                      # FastAPI backend
│   ├── anomaly/              # Anomaly detection strategies
│   ├── api/                  # API routes (public, admin, auth)
│   ├── auth/                 # JWT authentication
│   ├── config/               # Settings and configuration
│   ├── db/                   # Database connection
│   ├── schemas/              # Pydantic models
│   ├── services/             # Business logic
│   └── main.py               # Application entry point
├── worker/                   # Background worker
│   ├── youtube_client.py     # YouTube API client
│   ├── tasks.py              # Poll and cleanup tasks
│   ├── scheduler.py          # APScheduler setup
│   └── main.py               # Worker entry point
├── frontend-widget/          # Embeddable React widget
│   └── src/
│       ├── components/       # UI components
│       ├── hooks/            # Custom React hooks
│       └── api/              # API client
├── frontend-admin/           # Admin dashboard
│   └── src/
│       ├── pages/            # Route pages
│       ├── components/       # UI components
│       ├── context/          # Auth context
│       └── hooks/            # Data fetching hooks
├── db/                       # Database files
│   ├── schema.sql            # Table definitions
│   └── seed_data.sql         # Sample data
├── tests/                    # Test suites
├── docker-compose.yml        # Docker orchestration
└── .env.example              # Environment template
```

## 📡 API Endpoints

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/livestreams?count=10` | Get top N trending streams |
| GET | `/api/v1/health` | Health check |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login and get JWT token |

### Admin Endpoints (JWT Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/livestreams` | List all livestreams |
| POST | `/api/v1/admin/livestreams` | Create new livestream |
| GET | `/api/v1/admin/livestreams/{id}` | Get single livestream |
| PUT | `/api/v1/admin/livestreams/{id}` | Update livestream |
| DELETE | `/api/v1/admin/livestreams/{id}` | Delete livestream |
| GET | `/api/v1/admin/livestreams/{id}/history` | Get viewership history |

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=mysql+asyncmy://user:pass@mysql:3306/streamrank

# JWT Authentication
JWT_SECRET=your-secret-key-min-32-chars
JWT_EXPIRY_HOURS=24

# API Cache
CACHE_TTL_MINUTES=5

# YouTube API
YOUTUBE_API_KEY=your-youtube-api-key

# Worker
POLL_INTERVAL_MINUTES=3
RETENTION_DAYS=30
```

## 🧪 Anomaly Detection

StreamRank uses a pluggable strategy pattern for anomaly detection. Two algorithms are included:

### 1. Quantile-Based (Default)

Compares recent viewership against historical percentiles:
- Recent window: Last 15 minutes
- Baseline: Last 24 hours
- Score = how far recent is above the 75th percentile

### 2. Z-Score Based

Measures standard deviations from the mean:
- Calculates baseline mean and standard deviation
- Z-score = (recent_mean - baseline_mean) / baseline_std
- Optionally uses MAD (Median Absolute Deviation) for robustness

### Switching Algorithms

Edit `app/config/settings.py` or set environment variable:

```bash
ANOMALY_ALGORITHM=zscore  # Options: quantile, zscore
```

### Adding New Algorithms

1. Create a new strategy in `app/anomaly/`:

```python
# app/anomaly/my_strategy.py
from app.anomaly.protocol import AnomalyStrategy

class MyCustomStrategy(AnomalyStrategy):
    @property
    def name(self) -> str:
        return "custom"
    
    def calculate_score(
        self,
        recent_data: list[int],
        baseline_data: list[int],
    ) -> tuple[float, dict]:
        # Your algorithm here
        score = ...
        return score, {"debug": "info"}
```

2. Register in `app/anomaly/factory.py`:

```python
from .my_strategy import MyCustomStrategy

def get_anomaly_strategy(algorithm: str) -> AnomalyStrategy:
    strategies = {
        "quantile": QuantileStrategy,
        "zscore": ZScoreStrategy,
        "custom": MyCustomStrategy,  # Add here
    }
    return strategies[algorithm]()
```

## 📺 Adding New Livestreams

### Via Admin UI

1. Log in at http://localhost:3001
2. Click "Add Livestream"
3. Enter YouTube URL or video ID
4. Fill in name and channel
5. Save

### Via API

```bash
curl -X POST http://localhost:8000/api/v1/admin/livestreams \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url_or_id": "dQw4w9WgXcQ",
    "name": "My Livestream",
    "channel": "Channel Name"
  }'
```

## 🌐 Deploying the Widget

### Build for Production

```bash
cd frontend-widget
npm install
npm run build
```

### Deploy to GitHub Pages

1. Copy `dist/` contents to your GitHub Pages repo
2. Or use GitHub Actions:

```yaml
# .github/workflows/deploy-widget.yml
name: Deploy Widget
on:
  push:
    branches: [main]
    paths: ['frontend-widget/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: cd frontend-widget && npm ci && npm run build
      - uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./frontend-widget/dist
```

### Embedding the Widget

```html
<!-- As iframe -->
<iframe 
  src="https://your-site.github.io/widget/?count=10&theme=dark" 
  width="100%" 
  height="600" 
  frameborder="0">
</iframe>

<!-- Widget Parameters -->
<!-- count: Number of streams (1-100, default: 10) -->
<!-- refreshMinutes: Refresh interval (default: 5) -->
<!-- apiBaseUrl: API endpoint (default: http://localhost:8000/api/v1) -->
<!-- theme: light or dark (default: light) -->
```

## 🧪 Running Tests

```bash
# Backend tests
cd stream_rank
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Frontend widget tests
cd frontend-widget
npm test

# Frontend admin tests
cd frontend-admin
npm test
```

## 🔒 Security Considerations

1. **Change default credentials** in production
2. **Use strong JWT secret** (min 32 characters)
3. **Secure YouTube API key** (restrict by IP/referrer)
4. **Enable HTTPS** in production
5. **Review CORS settings** for production

## 🐳 Docker Commands

```bash
# Start production stack (mysql + api + worker only)
docker compose -f docker-compose.yml up -d

# Start with Admin UI + Widget
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Rebuild after code changes
docker compose -f docker-compose.yml up --build -d

# View logs
docker compose logs -f api
docker compose logs -f worker

# Stop services
docker compose down

# Reset database
docker compose down -v
docker compose -f docker-compose.yml up -d

# Shell into container
docker compose exec api bash
docker compose exec mysql mysql -u root -p
```

## 📊 Database

### Schema

```sql
-- Livestreams metadata
CREATE TABLE livestreams (
    id INT PRIMARY KEY AUTO_INCREMENT,
    youtube_video_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    channel VARCHAR(255) NOT NULL,
    description TEXT,
    url VARCHAR(512) NOT NULL,
    is_live BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Time series viewership data
CREATE TABLE viewership_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    livestream_id INT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    viewcount INT NOT NULL,
    FOREIGN KEY (livestream_id) REFERENCES livestreams(id) ON DELETE CASCADE
);

-- Admin users
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Manual Cleanup

```sql
-- Delete data older than 30 days
CALL cleanup_old_viewership_data(30, 1000);
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- [YouTube Data API](https://developers.google.com/youtube/v3)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Recharts](https://recharts.org/)
