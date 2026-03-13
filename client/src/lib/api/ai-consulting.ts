import { fetchJson } from "@/lib/http/client";
import type {
  EarningsResponse,
  PerResponse,
  ReportResponse,
  StocksResponse,
} from "@/types/ai_consulting";

// ── GUI管理銘柄 ──────────────────────────────────────────────────────────────

export async function listStocks(): Promise<StocksResponse> {
  return fetchJson<StocksResponse>("/api/ai-consulting/stocks");
}

export async function addStock(code: string): Promise<StocksResponse> {
  return fetchJson<StocksResponse>("/api/ai-consulting/stocks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
}

export async function deleteStock(code: string): Promise<StocksResponse> {
  return fetchJson<StocksResponse>(
    `/api/ai-consulting/stocks/${encodeURIComponent(code)}`,
    { method: "DELETE" },
  );
}

export async function refreshStock(code: string): Promise<StocksResponse> {
  return fetchJson<StocksResponse>(
    `/api/ai-consulting/stocks/${encodeURIComponent(code)}/refresh`,
    { method: "POST" },
  );
}

export async function refreshAllStocks(): Promise<StocksResponse> {
  return fetchJson<StocksResponse>("/api/ai-consulting/stocks/refresh-all", {
    method: "POST",
  });
}

// ── 既存エンドポイント ────────────────────────────────────────────────────────

export async function getAiConsultingPer(): Promise<PerResponse> {
  return fetchJson<PerResponse>("/api/ai-consulting/per");
}

export async function getAiConsultingEarnings(): Promise<EarningsResponse> {
  return fetchJson<EarningsResponse>("/api/ai-consulting/earnings");
}

export async function generateAiConsultingReport(): Promise<ReportResponse> {
  return fetchJson<ReportResponse>("/api/ai-consulting/report", {
    method: "POST",
  });
}
