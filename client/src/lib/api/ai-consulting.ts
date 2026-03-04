import { fetchJson } from "@/lib/http/client";
import type {
  PerResponse,
  EarningsResponse,
  ReportResponse,
} from "@/types/ai_consulting";

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
