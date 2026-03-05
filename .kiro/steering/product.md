---
inclusion: always
---

# Capital Lens — Product Context

Capital Lens is a market intelligence platform that generates weekly reports on Japanese and global capital markets.

## Product Purpose

Provide a consolidated view of capital market conditions and investment opportunities, with a focus on:
- Current market trends across asset classes
- Newly listed IPO companies in Japan
- AI and consulting sector analysis

The platform aggregates data from multiple sources and presents it in a unified dashboard, reducing the time needed to gather market intelligence.

## Target Users

- Investors and analysts tracking Japanese equity markets
- Professionals interested in IPO opportunities
- Those monitoring AI and consulting sector trends

Users expect timely, accurate data with minimal friction. The interface should be clean and information-dense.

## Core Features

### 1. Market Overview
Real-time snapshot of key market indicators:
- Japanese indices (Nikkei, TOPIX, Growth 250)
- US indices (S&P 500, NASDAQ, Dow, SOX)
- Risk indicators (VIX, Bitcoin)
- Bond yields (US 2Y, 10Y)
- FX rates (USD/JPY)
- Commodities (WTI crude, gold)

### 2. IPO Intelligence
Recent listings on Japanese exchanges (JPX):
- Company name, ticker, market segment
- Listing date and offering price
- On-demand AI-generated summaries from prospectus PDFs

### 3. AI × Consulting Sector Analysis
Focused analysis of AI and consulting companies:
- PER (Price-to-Earnings Ratio) comparison
- Upcoming earnings announcements
- Consolidated text report

## Weekly Output Concept

The platform is designed to support a weekly intelligence workflow:
- Data refreshes automatically or on-demand
- Users can access the dashboard anytime, but the intended cadence is weekly review
- Reports are generated on Friday to capture the week's activity

The system does not enforce a strict weekly schedule. Instead, it provides fresh data whenever accessed, allowing users to pull reports as needed.

## Scope and Non-Goals

### In Scope
- Aggregating public market data from free sources
- Presenting data in a clean, accessible format
- Generating AI summaries for IPO prospectuses
- Tracking a curated list of AI/consulting companies

### Out of Scope (for now)
- User authentication or personalization
- Historical data storage or trend analysis
- Trading recommendations or financial advice
- Real-time streaming data
- Mobile app
- Email delivery of reports
- Multi-language support beyond Japanese/English

## Design Philosophy

- Simplicity over feature bloat
- Fast load times and responsive UI
- Graceful degradation when external APIs fail
- Minimal user interaction required
- Data freshness over historical depth
