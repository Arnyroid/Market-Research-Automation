import { apiFetch } from "./client";

export interface TradeCreate {
  trade_date: string;      // YYYY-MM-DD
  symbol: string;
  exchange: string;
  company_name?: string;
  trade_type: "BUY" | "SELL";
  quantity: number;
  price: number;
  brokerage?: number;
  notes?: string;
}

export interface TradeOut {
  id: number;
  trade_date: string;
  symbol: string;
  exchange: string;
  company_name: string | null;
  trade_type: string;
  quantity: number;
  price: number;
  brokerage: number;
  realized_pnl: number | null;
}

export const tradesApi = {
  list:  (symbol?: string) =>
    apiFetch<TradeOut[]>(`/trades${symbol ? `?symbol=${encodeURIComponent(symbol)}` : ""}`),
  add:   (t: TradeCreate) =>
    apiFetch<TradeOut>("/trades", { method: "POST", body: JSON.stringify(t) }),
  remove: (id: number) =>
    apiFetch<void>(`/trades/${id}`, { method: "DELETE" }),
};
