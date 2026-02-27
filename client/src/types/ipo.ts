export type IpoItem = {
  company_name: string;
  ticker: string;
  market: string;
  listing_date: string;
  offering_price: number | null;
  summary: string;
  generated_at: string;
};

export type IpoLatestResponse = {
  items: IpoItem[];
  total_count: number;
  generated_at: string;
};
