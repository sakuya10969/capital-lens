import { fetchJson } from "@/lib/http/client";
import type { IpoLatestResponse, IpoSummaryResponse } from "@/types/ipo";

export async function getIpoLatest(
  signal?: AbortSignal,
): Promise<IpoLatestResponse> {
  return fetchJson<IpoLatestResponse>("/api/ipo/latest", { signal });
}

export async function getIpoSummary(code: string): Promise<IpoSummaryResponse> {
  return fetchJson<IpoSummaryResponse>(`/api/ipo/${code}/summary`);
}
