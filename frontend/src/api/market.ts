import { apiFetch } from "./client";

export interface IndustryNode {
  name: string;
  path: string;
  depth: number;          // 2, 3, or 4
  stock_count: number | null;   // only on L4 leaves
  total_stocks: number;         // sum of leaf stock_counts
  children: IndustryNode[];
}

export interface SectorInfo {
  code: string;           // e.g. IN08
  name: string;           // e.g. Information Technology
  path: string;           // e.g. /market/IN08/
  total_stocks: number;
  children: IndustryNode[];       // L2 nodes
  flat_industries: IndustryNode[];  // all L4 leaves, depth-first
}

export interface IndustryStock {
  rank: number;
  name: string;
  symbol: string | null;
  cmp: number | null;
  pe_ratio: number | null;
  market_cap: number | null;   // Cr
  div_yield: number | null;
  net_profit_qtr: number | null;
  qtr_profit_var: number | null;
  sales_qtr: number | null;
  qtr_sales_var: number | null;
  roce: number | null;
}

export interface IndustryPageResult {
  title: string;
  path: string;
  stocks: IndustryStock[];
  error: string | null;
  fetched_at: number;
}

export interface IndustryOverviewRow {
  rank:           number;
  name:           string;
  path:           string;         // /market/L1/L2/L3/L4/
  num_companies:  number | null;
  total_mktcap:   number | null;  // ₹ Cr
  median_mktcap:  number | null;  // ₹ Cr
  median_pe:      number | null;
  sales_growth:   number | null;  // Wtd. Avg Sales Growth %
  avg_opm:        number | null;  // Wtd. Avg OPM %
  avg_roce:       number | null;  // Wtd. Avg ROCE %
  return_1y:      number | null;  // Median 1Y Return %
}

export interface SectorSignal {
  name:        string;
  signal:      "BUY" | "HOLD" | "AVOID";
  rationale:   string;
  key_metrics: string;
}

export interface IndustrySignal {
  name:      string;
  signal:    "BUY" | "AVOID";
  rationale: string;
  metrics:   string;
}

export interface SectorAnalysis {
  market_summary:        string;
  generated_at:          string;
  sectors:               SectorSignal[];
  top_buy_industries:    IndustrySignal[];
  top_avoid_industries:  IndustrySignal[];
  disclaimer:            string;
  cached_at:             number;
}

export const marketApi = {
  getSectors: (force = false) =>
    apiFetch<SectorInfo[]>(`/market/sectors${force ? "?force=true" : ""}`),

  getOverview: (force = false) =>
    apiFetch<IndustryOverviewRow[]>(`/market/overview${force ? "?force=true" : ""}`),

  getSectorAnalysis: (force = false) =>
    apiFetch<SectorAnalysis>(`/market/sector-analysis${force ? "?force=true" : ""}`),

  getSectorStocks: (path: string, force = false) => {
    // path is e.g. "IN08" or "IN08/IN0801" — strip leading /market/ if present
    const clean = path.replace(/^\/market\//, "").replace(/\/$/, "");
    return apiFetch<IndustryPageResult>(
      `/market/sector/${clean}${force ? "?force=true" : ""}`
    );
  },
};
