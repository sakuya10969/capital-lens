---
inclusion: always
---

# Capital Lens — Technical Stack

## Architecture Overview

Capital Lens is a full-stack application with a clear separation between frontend and backend:
- Frontend: Next.js (React) with TypeScript
- Backend: FastAPI (Python) with async/await
- Communication: REST API over HTTP
- Deployment: Static export (frontend) + containerized API (backend)

## Frontend Stack

### Core Technologies
- Next.js 16 (App Router)
- React 19
- TypeScript 5
- Tailwind CSS 4

### Key Libraries
- `lucide-react` for icons
- `clsx` + `tailwind-merge` for conditional styling
- Custom UI components (card, table)

### Rendering Strategy
- Server-side rendering (SSR) for market overview
- Client-side rendering for IPO table and AI consulting (interactive features)
- Static generation where possible

### API Integration
- HTTP client abstracted in `src/lib/http/client.ts`
- API functions in `src/lib/api/` (market, ipo, ai-consulting)
- Type-safe responses using TypeScript interfaces

### Development
- Package manager: pnpm
- Dev server: `pnpm dev` (port 3000)
- Build: `pnpm build` (static export to `out/`)
- Linting: ESLint with Next.js config

## Backend Stack

### Core Technologies
- FastAPI (async web framework)
- Python 3.12+
- Pydantic for data validation
- uvicorn as ASGI server

### Key Libraries
- `yfinance` for market data (Yahoo Finance)
- `httpx` for async HTTP requests
- `beautifulsoup4` + `lxml` for HTML parsing
- `pdfplumber` for PDF text extraction
- `openai` for Azure OpenAI integration
- `pandas` for data manipulation
- `apscheduler` for potential scheduled tasks

### API Design
- RESTful endpoints under `/api/`
- JSON responses with Pydantic schemas
- CORS enabled for local development
- Global exception handlers for external API errors

### Service Layer
- Services encapsulate business logic
- Async-first design with `asyncio`
- Timeout protection on all external calls
- In-memory caching for expensive operations (24h TTL)

### Development
- Package manager: uv (Python)
- Dev server: `uvicorn src.main:app --reload`
- Formatting: black
- Environment: `.env` file for API keys

## Data Sources

### Market Data
- Yahoo Finance (via yfinance): indices, bonds, FX, commodities
- Free tier, no API key required
- Timeout: 15 seconds per request
- Parallel fetching with `asyncio.gather`

### IPO Data
- JPX (Japan Exchange Group) website
- Web scraping of public HTML tables
- PDF prospectus downloads for summaries
- Timeout: 15 seconds for HTML, 30 seconds for PDF

### AI Summaries
- Azure OpenAI (GPT-4 or similar)
- Requires `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`
- Used for IPO prospectus summarization
- Cached for 24 hours to reduce costs

### AI/Consulting Tickers
- Static JSON configuration: `server/config/ai_consulting_tickers.json`
- Manually curated list of company names and ticker symbols
- Fetched via yfinance for PER and earnings data

## Scheduling Concept

The current implementation is on-demand (data fetched when users access the dashboard).

For weekly automation:
- `apscheduler` is included in dependencies
- Could schedule tasks to pre-fetch and cache data every Friday
- Could trigger report generation and storage
- Not yet implemented — system is designed to support it

## Development Environment

### Prerequisites
- Node.js 20+ (frontend)
- Python 3.12+ (backend)
- pnpm (frontend package manager)
- uv (Python package manager)

### Local Setup
1. Backend: `cd server && uv sync && uvicorn src.main:app --reload`
2. Frontend: `cd client && pnpm install && pnpm dev`
3. Environment variables: `.env` files in both directories

### API Keys Required
- Azure OpenAI: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`
- No keys needed for yfinance or JPX scraping

## Deployment

### Backend
- Dockerfile provided in `server/`
- Deploy script: `server/deploy.sh`
- Runs as containerized service
- Environment variables injected at runtime

### Frontend
- Static export: `pnpm build` generates `out/` directory
- Can be hosted on any static file server
- Environment variable: `NEXT_PUBLIC_API_BASE_URL` points to backend

## Error Handling

- Custom exceptions: `ExternalAPIError`, `DataParsingError`
- Global exception handlers return structured JSON errors
- Frontend displays user-friendly error messages
- Graceful degradation: if one data source fails, others still render

## Performance Considerations

- Parallel data fetching reduces latency
- Timeouts prevent hanging requests
- In-memory caching for expensive operations
- Static generation where possible (frontend)
- Async I/O throughout backend
