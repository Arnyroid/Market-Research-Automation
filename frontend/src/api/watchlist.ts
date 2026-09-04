import { apiFetch } from "./client";

export interface WatchlistItem {
  id: number;
  symbol: string;
  exchange: string;
  company_name: string | null;
  sector: string | null;
  added_at: string;
}

export interface AddWatchlistPayload {
  symbol: string;
  exchange: string;
  company_name?: string;
  sector?: string;
}

export const watchlistApi = {
  list: ()                         => apiFetch<WatchlistItem[]>("/watchlist"),
  add:  (p: AddWatchlistPayload)   => apiFetch<WatchlistItem>("/watchlist", { method: "POST", body: JSON.stringify(p) }),
  remove: (id: number)             => apiFetch<void>(`/watchlist/${id}`, { method: "DELETE" }),
  search: (q: string)              => apiFetch<WatchlistItem[]>(`/watchlist/search?q=${encodeURIComponent(q)}`),
};
