import { fetchJson } from "@/lib/http/client";
import type { MarketOverviewResponse } from "@/types/market";

export async function getMarketOverview(): Promise<MarketOverviewResponse> {
  // `app/page.tsx` needs specific revalidation config
  return fetchJson<MarketOverviewResponse>("/api/market/overview", {
    next: { revalidate: 60 },
  });
}
