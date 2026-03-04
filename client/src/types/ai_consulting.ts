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
