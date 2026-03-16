// GUI管理銘柄
export interface StockRecord {
  code: string;
  symbol: string;
  name: string | null;
  enterprise_value: number | null;
  market_cap: number | null;
  per: number | null;
  revenue: number | null;
  operating_income: number | null;
  net_income: number | null;
  dividend_yield: number | null;
  roe: number | null;
  equity_ratio: number | null;
  updated_at: string | null;
  fetched_at?: string | null;
  price_as_of?: string | null;
  financials_as_of?: string | null;
}

export interface StocksResponse {
  stocks: StockRecord[];
}

// PER
export interface PerItem {
  name: string;
  symbol: string;
  price: number | null;
  currency: string | null;
  trailing_pe: number | null;
  forward_pe: number | null;
  trailing_eps: number | null;
  computed_pe: number | null;
  pe_used: "trailing" | "forward" | "computed" | null;
  website: string | null;
  note: string | null;
}

export interface PerResponse {
  as_of: string;
  items: PerItem[];
}

// Earnings
export interface EarningsItem {
  name: string;
  symbol: string;
  earnings_date: string | null;
  price_change_5d: number | null;
  price_change_1m: number | null;
  trailing_pe: number | null;
  summary: string | null;
  website: string | null;
  note: string | null;
}

export interface EarningsWindow {
  from_date: string;
  to_date: string;
  days: number;
}

export interface EarningsResponse {
  as_of: string;
  window: EarningsWindow;
  upcoming: EarningsItem[];
  unknown: EarningsItem[];
}

// Report
export interface ReportResponse {
  as_of: string;
  per: PerResponse;
  earnings: EarningsResponse;
  text_report: string;
}
