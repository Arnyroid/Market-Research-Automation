import { apiFetch } from "./client";

export interface Quote {
  symbol: string;
  exchange: string;
  company_name: string | null;
  ltp: number;
  open: number | null;
  high: number | null;
  low: number | null;
  prev_close: number | null;
  volume: number | null;
  pct_change: number | null;
}

export interface OHLCVBar {
  timestamp: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume: number | null;
}

export const pricesApi = {
  getQuote:   (symbol: string, exchange: string, signal?: AbortSignal) =>
    apiFetch<Quote>(`/prices/${symbol}?exchange=${exchange}`, {}, signal),
  getHistory: (symbol: string, exchange: string, days = 30, signal?: AbortSignal) =>
    apiFetch<OHLCVBar[]>(`/prices/${symbol}/history?exchange=${exchange}&days=${days}`, {}, signal),
};
