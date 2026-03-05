---
inclusion: always
---

# Capital Lens — Repository Structure

## High-Level Layout

```
capital-lens/
├── client/          # Next.js frontend
├── server/          # FastAPI backend
├── .github/         # GitHub Actions workflows
└── .kiro/           # Kiro steering documents
```

The repository is a monorepo with clear separation between frontend and backend. Each has its own dependencies, build process, and deployment strategy.

## Frontend Structure (`client/`)

```
client/
├── src/
│   ├── app/                 # Next.js App Router
│   │   ├── layout.tsx       # Root layout
│   │   ├── page.tsx         # Home page (dashboard)
│   │   └── globals.css      # Global styles
│   ├── components/          # React components
│   │   ├── market-overview.tsx
│   │   ├── ipo-table.tsx
│   │   ├── ai-consulting.tsx
│   │   └── ui/              # Reusable UI primitives
│   ├── lib/
│   │   ├── api/             # API client functions
│   │   ├── http/            # HTTP client abstraction
│   │   ├── formatters/      # Data formatting utilities
│   │   └── utils.ts         # General utilities
│   └── types/               # TypeScript type definitions
├── public/                  # Static assets
├── package.json
├── next.config.ts
└── tsconfig.json
```

### Frontend Conventions

- Components are organized by feature (market, ipo, ai-consulting)
- UI primitives live in `components/ui/`
- API calls are abstracted in `lib/api/` (one file per feature)
- Types mirror backend schemas in `types/`
- Server components by default, client components marked with `"use client"`

### Where to Add Frontend Features

- New dashboard section → new component in `src/components/`
- New API endpoint → new function in `src/lib/api/`
- New data type → new file in `src/types/`
- New page → new route in `src/app/`

## Backend Structure (`server/`)

```
server/
├── src/
│   ├── main.py              # FastAPI app entry point
│   ├── core/
│   │   ├── config.py        # Settings (env vars, timeouts)
│   │   └── exceptions.py    # Custom exception classes
│   ├── routers/             # API route handlers
│   │   ├── market.py        # GET /api/market/overview
│   │   ├── ipo.py           # GET /api/ipo/latest, /api/ipo/summary/{code}
│   │   └── ai_consulting.py # GET /api/ai-consulting/*
│   ├── services/            # Business logic layer
│   │   ├── market.py
│   │   ├── ipo.py
│   │   └── ai_consulting.py
│   ├── schemas/             # Pydantic models (request/response)
│   │   ├── market.py
│   │   ├── ipo.py
│   │   └── ai_consulting.py
│   └── utils/               # Shared utilities
│       ├── yfinance.py      # Yahoo Finance helpers
│       ├── jpx_parser.py    # JPX HTML parsing
│       ├── pdf.py           # PDF text extraction
│       └── llm.py           # Azure OpenAI integration
├── config/
│   └── ai_consulting_tickers.json  # Curated ticker list
├── docs/
│   └── implementation_plan.md      # Original design doc
├── pyproject.toml
├── Dockerfile
└── deploy.sh
```

### Backend Conventions

- Routers handle HTTP concerns (request/response)
- Services contain business logic (data fetching, transformation)
- Schemas define data contracts (Pydantic models)
- Utils are reusable, stateless functions
- No database layer (in-memory only)

### Dependency Injection

Services are injected into routers using FastAPI's `Depends()`:

```python
@router.get("/api/market/overview")
async def get_market_overview(service: MarketService = Depends()):
    return await service.get_market_overview()
```

This keeps routers thin and services testable.

### Where to Add Backend Features

- New API endpoint → new router in `src/routers/`
- New data source → new service in `src/services/`
- New external API integration → new utility in `src/utils/`
- New response format → new schema in `src/schemas/`
- New configuration → add to `src/core/config.py`

## Shared Concepts

### Type Alignment

Frontend types (`client/src/types/`) should mirror backend schemas (`server/src/schemas/`). When adding a new API endpoint:

1. Define Pydantic schema in backend
2. Create matching TypeScript interface in frontend
3. Use the interface in API client function

### Error Handling

- Backend raises custom exceptions (`ExternalAPIError`, `DataParsingError`)
- Global exception handlers convert to structured JSON
- Frontend checks response status and displays user-friendly messages

### Configuration

- Backend: `.env` file in `server/` (API keys, timeouts)
- Frontend: `.env.local` in `client/` (API base URL)
- Ticker list: `server/config/ai_consulting_tickers.json`

## Testing Strategy (Future)

Currently no tests are implemented. When adding tests:

- Frontend: Jest + React Testing Library in `client/src/__tests__/`
- Backend: pytest in `server/tests/`
- E2E: Playwright in `tests/e2e/`

## Documentation

- Implementation plan: `server/docs/implementation_plan.md`
- Steering documents: `.kiro/steering/`
- README files in `client/` and `server/` (currently minimal)

## Deployment Artifacts

- Frontend: `client/out/` (static export)
- Backend: Docker image built from `server/Dockerfile`
- Deploy script: `server/deploy.sh` (backend only)

## General Guidelines

- Keep frontend and backend loosely coupled (communicate via REST API)
- Avoid duplicating logic between frontend and backend
- Use TypeScript/Pydantic for type safety
- Prefer async/await for I/O operations
- Handle errors gracefully at every layer
- Document complex logic with inline comments
- Keep configuration in environment variables, not hardcoded
