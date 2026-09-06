import { apiFetch } from "./client";

// ── Table section — mirrors TableSection dataclass ────────────────────────────
export interface TableSection {
  headers: string[];
  rows: Array<Record<string, string>>;   // each row has "_label" + one key per header
  unit: string;    // e.g. "Figures in Rs. Crores"
}

// ── Peer comparison row ────────────────────────────────────────────────────────
export interface PeerInfo {
  name: string;
  symbol: string | null;
  price: number | null;
  pe_ratio: number | null;
  market_cap: number | null;
  div_yield: number | null;
  net_profit: number | null;
  roce: number | null;
  sales_growth_3yr: number | null;
  sales_growth_5yr: number | null;
  roe_3yr: number | null;
}

// ── Full fundamentals payload — mirrors FundamentalsResult dataclass ───────────
export interface Fundamentals {
  symbol: string;

  // Core ratios
  pe_ratio: number | null;
  book_value: number | null;
  roce: number | null;
  roe: number | null;
  div_yield: number | null;
  market_cap: number | null;       // in Cr
  debt_to_equity: number | null;
  eps: number | null;
  face_value: number | null;

  // Shareholding
  promoter_pct: number | null;
  fii_pct: number | null;
  dii_pct: number | null;
  public_pct: number | null;

  // Full table sections
  quarterly_results: TableSection | null;
  profit_loss: TableSection | null;
  balance_sheet: TableSection | null;
  cash_flow: TableSection | null;
  key_ratios: TableSection | null;

  // Growth rates
  sales_growth_3yr: number | null;
  sales_growth_5yr: number | null;
  profit_growth_3yr: number | null;
  profit_growth_5yr: number | null;

  // Convenience OPM list
  opm_trend: number[];

  // Industry
  sector: string | null;
  industry: string | null;

  // Pros / Cons
  pros: string[];
  cons: string[];

  // Peers
  peers: PeerInfo[];
  // Industry median P/E and total tracked company count (from screener.in Median row)
  industry_pe_median: number | null;
  industry_peer_count: number | null;

  // Metadata
  fetched_at: number;
  error: string | null;
}

export const fundamentalsApi = {
  get: (symbol: string, exchange = "NSE", force = false, signal?: AbortSignal) =>
    apiFetch<Fundamentals>(
      `/analysis/${symbol}/fundamentals?exchange=${exchange}${force ? "&force=true" : ""}`,
      {},
      signal
    ),
};
