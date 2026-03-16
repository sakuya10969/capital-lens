import { fetchJson } from "@/lib/http/client";
import type { MarketOverviewResponse } from "@/types/market";

export async function getMarketOverview(): Promise<MarketOverviewResponse> {
  return fetchJson<MarketOverviewResponse>("/api/market/overview", {
    next: { revalidate: 60 },
  });
}
