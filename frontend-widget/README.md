# Trending Livestreams Widget

A modern, embeddable React widget for displaying trending YouTube livestreams.

## Features

- 📊 Real-time trending livestream rankings
- 🎬 Embedded YouTube player
- 📈 Viewership history charts (Recharts)
- 🌙 Dark/Light mode support
- 📱 Responsive design
- ⚙️ Configurable via URL parameters
- 🚀 Static build for GitHub Pages

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test
```

## Configuration

The widget accepts the following URL parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `count` | number | 10 | Number of streams to display (max: 100) |
| `refreshMinutes` | number | 5 | Polling interval in minutes |
| `apiBaseUrl` | string | http://localhost:8000/api/v1 | API endpoint |
| `theme` | "light" \| "dark" | "light" | Color theme |

### Example URLs

```
# Default settings
https://your-site.github.io/widget/

# Dark mode with 20 streams
https://your-site.github.io/widget/?theme=dark&count=20

# Custom API endpoint
https://your-site.github.io/widget/?apiBaseUrl=https://api.example.com/v1

# All options
https://your-site.github.io/widget/?count=15&refreshMinutes=10&theme=dark&apiBaseUrl=https://api.example.com/v1
```

## Embedding

### Via iframe

```html
<iframe 
  src="https://your-site.github.io/widget/?theme=dark&count=10"
  width="100%"
  height="800"
  frameborder="0"
  title="Trending Livestreams"
></iframe>
```

### Direct Include

Host the built files and include directly in your page:

```html
<div id="trending-streams-widget"></div>
<script type="module" src="https://your-site.github.io/widget/assets/index.js"></script>
```

## API Integration

The widget expects the following API endpoints:

### GET /livestreams

Returns a list of trending livestreams.

**Query Parameters:**
- `count` (number): Number of streams to return (1-100)

**Response:**
```json
{
  "items": [
    {
      "id": "string",
      "youtube_video_id": "string",
      "name": "string",
      "channel": "string",
      "url": "string",
      "is_live": true,
      "current_viewers": 12345,
      "rank": 1,
      "trend_score": 85
    }
  ],
  "count": 10,
  "cached_at": "2024-01-01T00:00:00Z"
}
```

### GET /streams/{video_id}/viewership

Returns viewership history for a specific stream.

**Query Parameters:**
- `hours` (number): Number of hours of history to return (default: 24)

**Response:**
```json
{
  "video_id": "string",
  "history": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "viewers": 10000
    }
  ],
  "period_hours": 24
}
```

## Development

### Mock Data

During development, the widget uses mock data by default. To use a real API:

1. Create a `.env.local` file:
   ```
   VITE_USE_REAL_API=true
   ```

2. Ensure your API is running at the configured `apiBaseUrl`

### Project Structure

```
frontend-widget/
├── src/
│   ├── App.tsx              # Main application component
│   ├── main.tsx             # Entry point
│   ├── index.css            # Global styles with Tailwind
│   ├── components/
│   │   ├── StreamList.tsx   # List of stream cards
│   │   ├── StreamCard.tsx   # Individual stream card
│   │   ├── YouTubePlayer.tsx # Embedded YouTube player
│   │   ├── ViewershipChart.tsx # Recharts line chart
│   │   └── LoadingSpinner.tsx  # Loading states
│   ├── hooks/
│   │   ├── useConfig.ts     # URL parameter parsing
│   │   └── useStreams.ts    # Data fetching hooks
│   ├── types/
│   │   └── index.ts         # TypeScript interfaces
│   ├── api/
│   │   └── client.ts        # API client & mock data
│   └── test/
│       └── *.test.ts        # Component tests
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## Building for GitHub Pages

1. Update `vite.config.ts` base path if needed:
   ```ts
   base: '/your-repo-name/',
   ```

2. Build the project:
   ```bash
   npm run build
   ```

3. The `dist/` folder contains all static files ready for deployment.

## License

MIT
