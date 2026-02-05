# Stream Rank Admin Dashboard

A modern admin dashboard for managing and monitoring YouTube livestreams.

## Features

- 🔐 **Authentication**: JWT-based login with secure token storage
- 📊 **Dashboard**: Overview stats and quick actions
- 📺 **Livestream Management**: Full CRUD operations for streams
- 📈 **Viewership Analytics**: Charts and raw data tables
- 🔍 **Search & Filter**: Find streams quickly
- 🎨 **Modern UI**: Clean, professional design with Tailwind CSS

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Router** - Navigation
- **TanStack Query** - Data fetching & caching
- **React Hook Form** - Form handling
- **Recharts** - Data visualization
- **React Hot Toast** - Notifications

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:5174`

### Building for Production

```bash
npm run build
```

### Running Tests

```bash
# Run tests
npm run test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

## Project Structure

```
src/
├── api/           # API client and endpoints
├── components/    # Reusable UI components
├── context/       # React contexts (Auth)
├── hooks/         # Custom React hooks
├── pages/         # Page components
├── test/          # Test files
└── types/         # TypeScript type definitions
```

## API Integration

The dashboard connects to the Stream Rank API with the following endpoints:

- `POST /auth/login` - User authentication
- `GET /admin/livestreams` - List all livestreams
- `POST /admin/livestreams` - Add new livestream
- `GET /admin/livestreams/:id` - Get livestream details
- `PUT /admin/livestreams/:id` - Update livestream
- `DELETE /admin/livestreams/:id` - Delete livestream
- `GET /admin/livestreams/:id/history` - Get viewership history
- `GET /admin/stats` - Get dashboard statistics

## Environment Configuration

The Vite dev server proxies `/api` requests to `http://localhost:8000`. For production, configure your reverse proxy accordingly.

## License

MIT
