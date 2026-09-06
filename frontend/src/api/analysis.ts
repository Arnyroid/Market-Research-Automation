import { apiFetch } from "./client";

export interface Analysis {
  id: number;
  symbol: string;
  exchange: string;
  generated_at: string;
  risk_flag: string | null;
  indicators_snapshot: Record<string, unknown> | null;
  structured_output: {
    summary: string;
    recommendation: "BUY" | "HOLD" | "SELL" | "AVOID";
    rationale: string;
    risk_flag: string;
    caveats: string;
    disclaimer: string;
  } | null;
  llm_output: string | null;
  target_review_date: string | null;
}

export const analysisApi = {
  getLatest:  (symbol: string, exchange: string) =>
    apiFetch<Analysis>(`/analysis/${symbol}?exchange=${exchange}`),
  refresh:    (symbol: string, exchange: string) =>
    apiFetch<{ detail: string }>(`/analysis/${symbol}/refresh?exchange=${exchange}`, { method: "POST" }),
  getHistory: (symbol: string, exchange: string, limit = 5) =>
    apiFetch<Analysis[]>(`/analysis/${symbol}/history?exchange=${exchange}&limit=${limit}`),
};
