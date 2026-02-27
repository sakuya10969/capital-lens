export type MarketItem = {
  name: string;
  current_price: number;
  change: number;
  change_percent: number;
};

export type MarketOverviewResponse = {
  indices: MarketItem[];
  risk_indicators: MarketItem[];
  bonds: MarketItem[];
  fx: MarketItem[];
  commodities: MarketItem[];
  generated_at: string;
};
