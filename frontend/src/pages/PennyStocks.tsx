import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { RefreshCw, TrendingUp, TrendingDown, Minus, Search, SlidersHorizontal, AlertTriangle } from "lucide-react";
import { apiFetch } from "../api/client";
import { useSortFilter } from "../hooks/useSortFilter";
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface PennyStock {
  rank:              number;
  name:              string;
  symbol:            string | null;
  cmp:               number | null;
  market_cap:        number | null;
  pe_ratio:          number | null;
  roce:              number | null;
  div_yield:         number | null;
  net_profit_qtr:    number | null;
  qtr_sales_var:     number | null;
  high_52w:          number | null;
  low_52w:           number | null;
  pct_from_52w_high: number | null;
}

interface PennyResponse {
  stocks:  PennyStock[];
  count:   number;
  filters: { max_price: number; min_market_cap_cr: number; max_market_cap_cr: number };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtInr(n: number | null) {
  if (n == null) return <span className="text-gray-600">—</span>;
  return `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtCr(n: number | null) {
  if (n == null) return <span className="text-gray-600">—</span>;
  if (n >= 1000) return `₹${(n / 1000).toFixed(1)}k Cr`;
  return `₹${n.toFixed(0)} Cr`;
}

function fmtPct(n: number | null, alwaysSign = false) {
  if (n == null) return <span className="text-gray-600">—</span>;
  const sign = alwaysSign && n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}

function VarCell({ v }: { v: number | null }) {
  if (v == null) return <span className="text-gray-600">—</span>;
  const cls  = v > 0 ? "text-emerald-400" : v < 0 ? "text-red-400" : "text-gray-400";
  const Icon = v > 0 ? TrendingUp : v < 0 ? TrendingDown : Minus;
  return (
    <span className={`${cls} inline-flex items-center gap-0.5`}>
      <Icon size={10} />
      {v > 0 ? "+" : ""}{v.toFixed(1)}%
    </span>
  );
}

// ── Sortable header ───────────────────────────────────────────────────────────

function SortTh({ label, sortKey, current, dir, onSort, className = "" }: {
  label: string; sortKey: string; current: string; dir: "asc" | "desc";
  onSort: (k: string) => void; className?: string;
}) {
  const active = current === sortKey;
  return (
    <th
      className={`th cursor-pointer select-none hover:text-white transition-colors ${className}`}
      onClick={() => onSort(sortKey)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {active
          ? dir === "asc"
            ? <ChevronUp size={12} className="text-blue-400" />
            : <ChevronDown size={12} className="text-blue-400" />
          : <ChevronsUpDown size={12} className="text-gray-500" />}
      </span>
    </th>
  );
}

// ── Price ceiling presets ─────────────────────────────────────────────────────

const PRICE_PRESETS = [
  { label: "≤ ₹10",  value: 10  },
  { label: "≤ ₹20",  value: 20  },
  { label: "≤ ₹50",  value: 50  },
  { label: "≤ ₹100", value: 100 },
];

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PennyStocksPage() {
  const navigate = useNavigate();

  const [data, setData]       = useState<PennyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  // Filter state
  const [maxPrice,    setMaxPrice]    = useState(50);
  const [minMcap,     setMinMcap]     = useState(10);
  const [maxMcap,     setMaxMcap]     = useState(500);
  const [textFilter,  setTextFilter]  = useState("");
  const [showFilters, setShowFilters] = useState(false);

  // Pending filter inputs (applied on "Run Screen")
  const [pendingMax,  setPendingMax]  = useState(50);
  const [pendingMinMc, setPendingMinMc] = useState(10);
  const [pendingMaxMc, setPendingMaxMc] = useState(500);

  function fetchData(mp = maxPrice, minMc = minMcap, maxMc = maxMcap, force = false) {
    setLoading(true);
    setError(null);
    apiFetch<PennyResponse>(
      `/market/penny-stocks?max_price=${mp}&min_market_cap_cr=${minMc}&max_market_cap_cr=${maxMc}${force ? "&force=true" : ""}`
    )
      .then(d => { setData(d); setMaxPrice(mp); setMinMcap(minMc); setMaxMcap(maxMc); })
      .catch(e => setError(e.message ?? "Failed to load penny stocks"))
      .finally(() => setLoading(false));
  }

  // Load on mount
  useEffect(() => { fetchData(); }, []);

  const stocks = data?.stocks ?? [];

  const { filtered, sortKey, sortDir, setSort } = useSortFilter(stocks, {
    textKeys: ["name", "symbol"],
    getValue: (r, key) => {
      switch (key) {
        case "name":     return r.name;
        case "symbol":   return r.symbol ?? "";
        case "cmp":      return r.cmp             ?? -Infinity;
        case "mcap":     return r.market_cap       ?? -Infinity;
        case "pe":       return r.pe_ratio         ?? -Infinity;
        case "roce":     return r.roce             ?? -Infinity;
        case "52h_pct":  return r.pct_from_52w_high ?? -Infinity;
        case "qsv":      return r.qtr_sales_var    ?? -Infinity;
        case "np":       return r.net_profit_qtr   ?? -Infinity;
        default:         return "";
      }
    },
    defaultSortKey: "mcap",
    defaultSortDir: "desc",
    numericKeys: ["cmp", "mcap", "pe", "roce", "52h_pct", "qsv", "np"],
  });

  const displayed = useMemo(() => {
    const q = textFilter.trim().toLowerCase();
    if (!q) return filtered;
    return filtered.filter(r =>
      r.name.toLowerCase().includes(q) || (r.symbol ?? "").toLowerCase().includes(q)
    );
  }, [filtered, textFilter]);

  // Stats bar
  const { profitable, withRoce } = useMemo(() => ({
    profitable: stocks.filter(s => (s.net_profit_qtr ?? 0) > 0).length,
    withRoce:   stocks.filter(s => (s.roce ?? 0) > 15).length,
  }), [stocks]);

  return (
    <div className="p-6 max-w-6xl mx-auto">

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Penny Stocks</h1>
          <p className="text-gray-400 text-sm mt-1">
            NSE/BSE equities under ₹{maxPrice} · screener.in live screen · 1h cache
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(v => !v)}
            className={`btn-ghost flex items-center gap-1.5 text-sm ${showFilters ? "text-blue-400" : ""}`}
          >
            <SlidersHorizontal size={14} />
            Filters
          </button>
          <button
            onClick={() => fetchData(maxPrice, minMcap, maxMcap, true)}
            disabled={loading}
            className="btn-primary flex items-center gap-1.5 text-sm"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            {loading ? "Screening…" : "Refresh"}
          </button>
        </div>
      </div>

      {/* Filter panel */}
      {showFilters && (
        <div className="card mb-5 p-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Screen Filters</p>

          {/* Price ceiling presets */}
          <div className="mb-4">
            <p className="text-xs text-gray-500 mb-2">Max Price</p>
            <div className="flex gap-2 flex-wrap">
              {PRICE_PRESETS.map(p => (
                <button
                  key={p.value}
                  onClick={() => setPendingMax(p.value)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    pendingMax === p.value
                      ? "border-blue-500 bg-blue-500/15 text-blue-300"
                      : "border-gray-700 text-gray-400 hover:border-gray-500 hover:text-white"
                  }`}
                >
                  {p.label}
                </button>
              ))}
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-gray-500">Custom ₹</span>
                <input
                  type="number" min="1" max="500" step="1"
                  value={pendingMax}
                  onChange={e => setPendingMax(Number(e.target.value))}
                  className="input w-20 text-xs py-1.5"
                />
              </div>
            </div>
          </div>

          {/* Market cap range */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-xs text-gray-500 mb-1.5">Min Market Cap (₹ Cr)</p>
              <input
                type="number" min="1" step="1"
                value={pendingMinMc}
                onChange={e => setPendingMinMc(Number(e.target.value))}
                className="input text-xs py-1.5 w-full"
              />
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1.5">Max Market Cap (₹ Cr)</p>
              <input
                type="number" min="1" step="10"
                value={pendingMaxMc}
                onChange={e => setPendingMaxMc(Number(e.target.value))}
                className="input text-xs py-1.5 w-full"
              />
            </div>
          </div>

          <button
            className="btn-primary text-sm"
            onClick={() => { fetchData(pendingMax, pendingMinMc, pendingMaxMc); setShowFilters(false); }}
            disabled={loading}
          >
            Run Screen
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-start gap-3 bg-red-900/20 border border-red-800/40 rounded-xl px-4 py-3 mb-5 text-sm text-red-400">
          <AlertTriangle size={16} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-medium mb-0.5">Screen unavailable</p>
            <p className="text-xs text-red-500/80">{error}</p>
            {error.includes("SCREENER_EMAIL") && (
              <p className="text-xs text-gray-500 mt-1">
                Add <code className="bg-gray-800 px-1 rounded">SCREENER_EMAIL</code> and{" "}
                <code className="bg-gray-800 px-1 rounded">SCREENER_PASSWORD</code> to your{" "}
                <code className="bg-gray-800 px-1 rounded">.env</code> file and restart the server.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Loading skeleton */}
      {loading && !data && (
        <div className="flex items-center justify-center gap-2 text-gray-500 text-sm py-20">
          <RefreshCw size={16} className="animate-spin" />
          Running screener.in screen query…
        </div>
      )}

      {/* Results */}
      {data && !loading && (
        <>
          {/* Stats bar */}
          <div className="flex flex-wrap items-center gap-4 mb-4 text-sm">
            <span className="text-gray-400">{data.count} stocks matched</span>
            {profitable > 0 && (
              <span className="text-emerald-400">✓ {profitable} profitable (qtr)</span>
            )}
            {withRoce > 0 && (
              <span className="text-blue-400">★ {withRoce} ROCE &gt; 15%</span>
            )}
            <span className="text-gray-600 text-xs ml-auto">
              Screen: price &lt; ₹{data.filters.max_price} · MCap ₹{data.filters.min_market_cap_cr}–{data.filters.max_market_cap_cr} Cr
            </span>
          </div>

          {/* Text filter */}
          <div className="mb-3 relative max-w-xs">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              className="input pl-8 text-sm py-2"
              placeholder="Filter by name or symbol…"
              value={textFilter}
              onChange={e => setTextFilter(e.target.value)}
            />
          </div>

          {/* Table */}
          <div className="card p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-800/60">
                    <SortTh label="Company"   sortKey="name"   current={sortKey} dir={sortDir} onSort={setSort} className="text-left" />
                    <SortTh label="CMP ₹"     sortKey="cmp"    current={sortKey} dir={sortDir} onSort={setSort} className="text-right" />
                    <SortTh label="Mkt Cap"   sortKey="mcap"   current={sortKey} dir={sortDir} onSort={setSort} className="text-right" />
                    <SortTh label="P/E"       sortKey="pe"     current={sortKey} dir={sortDir} onSort={setSort} className="text-right" />
                    <SortTh label="ROCE %"    sortKey="roce"   current={sortKey} dir={sortDir} onSort={setSort} className="text-right" />
                    <SortTh label="Qtr Sales" sortKey="qsv"   current={sortKey} dir={sortDir} onSort={setSort} className="text-right" />
                    <SortTh label="NP Qtr"    sortKey="np"    current={sortKey} dir={sortDir} onSort={setSort} className="text-right" />
                  </tr>
                </thead>
                <tbody>
                  {displayed.length === 0 && (
                    <tr>
                      <td colSpan={7} className="td text-center text-gray-600 py-8">
                        No stocks match the current filters.
                      </td>
                    </tr>
                  )}
                  {displayed.map((s, i) => {
                    return (
                      <tr
                        key={i}
                        className={`border-t border-gray-800/40 hover:bg-gray-800/30 transition-colors ${s.symbol ? "cursor-pointer" : ""}`}
                        onClick={() => s.symbol && navigate(`/stock/${s.symbol}?exchange=NSE`)}
                      >
                        {/* Company */}
                        <td className="td">
                          <div className="font-medium text-gray-200 leading-tight">{s.name || "—"}</div>
                          {s.symbol && (
                            <div className="font-mono text-[10px] text-gray-500 mt-0.5">{s.symbol}</div>
                          )}
                        </td>

                        {/* CMP */}
                        <td className="td text-right font-mono text-white font-semibold">
                          {s.cmp != null ? `₹${s.cmp.toFixed(2)}` : "—"}
                        </td>

                        {/* Market cap */}
                        <td className="td text-right font-mono text-gray-300">{fmtCr(s.market_cap)}</td>

                        {/* P/E */}
                        <td className="td text-right font-mono text-gray-300">
                          {s.pe_ratio != null ? s.pe_ratio.toFixed(1) : <span className="text-gray-600">—</span>}
                        </td>

                        {/* ROCE */}
                        <td className={`td text-right font-mono ${
                          s.roce == null ? "text-gray-600"
                            : s.roce >= 15  ? "text-emerald-400"
                            : s.roce >= 8   ? "text-yellow-400"
                            : "text-red-400"
                        }`}>
                          {s.roce != null ? `${s.roce.toFixed(1)}%` : "—"}
                        </td>

                        {/* Qtr Sales Var */}
                        <td className="td text-right"><VarCell v={s.qtr_sales_var} /></td>

                        {/* Net Profit Qtr */}
                        <td className={`td text-right font-mono ${
                          s.net_profit_qtr == null ? "text-gray-600"
                            : s.net_profit_qtr > 0  ? "text-emerald-400"
                            : "text-red-400"
                        }`}>
                          {s.net_profit_qtr != null
                            ? `${s.net_profit_qtr >= 0 ? "+" : ""}₹${Math.abs(s.net_profit_qtr).toFixed(1)} Cr`
                            : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <p className="text-[10px] text-gray-700 mt-3 text-right">
            Data sourced from screener.in · 1h cache · Not investment advice
          </p>
        </>
      )}
    </div>
  );
}
