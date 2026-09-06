import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, BarChart, Bar, Legend,
} from "recharts";
import { RefreshCw, AlertTriangle, TrendingUp, Bell, PlusCircle, ExternalLink, ChevronDown, ChevronUp } from "lucide-react";
import { pricesApi, OHLCVBar } from "../api/prices";
import { analysisApi, Analysis } from "../api/analysis";
import { fundamentalsApi, Fundamentals, TableSection } from "../api/fundamentals";

// ── Constants ─────────────────────────────────────────────────────────────────

const RISK_BADGE: Record<string, string> = {
  low:    "badge-low",
  medium: "badge-medium",
  high:   "badge-high",
};

const REC_STYLE: Record<string, string> = {
  BUY:   "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
  HOLD:  "bg-blue-500/15 text-blue-400 border border-blue-500/30",
  SELL:  "bg-red-500/15 text-red-400 border border-red-500/30",
  AVOID: "bg-yellow-500/15 text-yellow-400 border border-yellow-500/30",
};

const REC_ICON: Record<string, string> = {
  BUY: "▲", HOLD: "◆", SELL: "▼", AVOID: "⊘",
};

// ── Indicator computations (client-side, from raw OHLCV) ─────────────────────

/** Simple moving average over `period` bars */
function sma(closes: number[], period: number): (number | null)[] {
  return closes.map((_, i) => {
    if (i < period - 1) return null;
    const slice = closes.slice(i - period + 1, i + 1);
    return slice.reduce((a, b) => a + b, 0) / period;
  });
}

/** Wilder-style EMA over `period` bars */
function ema(closes: number[], period: number): (number | null)[] {
  const k = 2 / (period + 1);
  const out: (number | null)[] = new Array(closes.length).fill(null);
  let prev: number | null = null;
  for (let i = 0; i < closes.length; i++) {
    if (i < period - 1) { out[i] = null; continue; }
    if (prev === null) {
      prev = closes.slice(0, period).reduce((a, b) => a + b, 0) / period;
      out[i] = prev;
    } else {
      prev = closes[i] * k + prev * (1 - k);
      out[i] = prev;
    }
  }
  return out;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function IndicatorTile({ label, value, sub }: { label: string; value: string | null; sub?: string }) {
  return (
    <div className="card py-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-lg font-semibold text-white">
        {value ?? <span className="text-gray-600 text-sm">—</span>}
      </p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

function FundTile({ label, value, sub, highlight }: {
  label: string; value: string | null; sub?: string; highlight?: "good" | "bad" | "neutral";
}) {
  const color = highlight === "good" ? "text-emerald-400"
              : highlight === "bad"  ? "text-red-400"
              : "text-white";
  return (
    <div className="bg-gray-800/60 rounded-xl px-4 py-3 border border-gray-700/40">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-base font-semibold ${color}`}>
        {value ?? <span className="text-gray-600 text-sm">—</span>}
      </p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

/** Small pill toggle for chart overlay lines */
function OverlayToggle({
  label, color, active, onClick,
}: { label: string; color: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium border transition-opacity ${
        active ? "opacity-100" : "opacity-30"
      }`}
      style={{ borderColor: color, color }}
    >
      <span className="inline-block w-5 h-0.5 rounded" style={{ background: color }} />
      {label}
    </button>
  );
}

/** Return true if the analysis is absent or was generated on a previous calendar day */
function isStale(a: Analysis | null): boolean {
  if (!a) return true;
  const today = new Date().toISOString().slice(0, 10);
  return a.generated_at.slice(0, 10) < today;
}

function fmt(n: number | null | undefined, decimals = 2, prefix = "", suffix = "") {
  if (n == null) return "—";
  return `${prefix}${n.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}${suffix}`;
}

// ── Collapsible section wrapper ───────────────────────────────────────────────

function CollapsibleSection({ title, defaultOpen = true, children }: {
  title: string; defaultOpen?: boolean; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card p-0 overflow-hidden mb-4">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-gray-800/30 transition-colors"
      >
        <span className="text-sm font-semibold text-white">{title}</span>
        {open ? <ChevronUp size={15} className="text-gray-400" /> : <ChevronDown size={15} className="text-gray-400" />}
      </button>
      {open && <div className="border-t border-gray-800">{children}</div>}
    </div>
  );
}

// ── Scrollable data table (for quarterly / annual sections) ───────────────────

function DataTable({ section, maxRows }: { section: TableSection; maxRows?: number }) {
  const rows = maxRows ? section.rows.slice(0, maxRows) : section.rows;
  // Reverse headers so newest period appears first (left-most data column)
  const headers = [...section.headers].reverse();
  return (
    <div className="overflow-x-auto relative">
      {/* Unit label — shown above the table */}
      {section.unit && (
        <p className="text-[11px] text-gray-500 px-4 pt-3 pb-1 italic">{section.unit}</p>
      )}
      <table className="text-xs border-collapse" style={{ minWidth: "max-content", width: "100%" }}>
        <thead>
          <tr className="bg-gray-800/60">
            <th
              className="th text-left whitespace-nowrap border-r border-gray-700/60"
              style={{ position: "sticky", left: 0, zIndex: 20, background: "#1a2030", minWidth: 160 }}
            >
              Item
            </th>
            {headers.map(h => (
              <th key={h} className="th text-right whitespace-nowrap" style={{ minWidth: 88 }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-gray-800/20 transition-colors border-b border-gray-800/40">
              <td
                className="td text-gray-200 font-medium whitespace-nowrap border-r border-gray-700/40"
                style={{ position: "sticky", left: 0, zIndex: 10, backgroundColor: "#111827" }}
              >
                {row["_label"]}
              </td>
              {headers.map(h => (
                <td key={h} className="td text-right font-mono text-gray-400">
                  {row[h] || "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Shareholding bar ───────────────────────────────────────────────────────────

function ShareholdingBar({ fund }: { fund: Fundamentals }) {
  const segments = [
    { label: "Promoter", pct: fund.promoter_pct, color: "#3b82f6" },
    { label: "FII",      pct: fund.fii_pct,      color: "#8b5cf6" },
    { label: "DII",      pct: fund.dii_pct,      color: "#06b6d4" },
    { label: "Public",   pct: fund.public_pct,   color: "#6b7280" },
  ].filter(s => s.pct != null && s.pct > 0);

  if (!segments.length) return null;

  return (
    <div>
      {/* Stacked bar */}
      <div className="flex rounded-full overflow-hidden h-3 mb-3">
        {segments.map(s => (
          <div
            key={s.label}
            style={{ width: `${s.pct}%`, background: s.color }}
            title={`${s.label}: ${s.pct!.toFixed(1)}%`}
          />
        ))}
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-4">
        {segments.map(s => (
          <div key={s.label} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm inline-block shrink-0" style={{ background: s.color }} />
            <span className="text-xs text-gray-400">{s.label}</span>
            <span className="text-xs font-semibold text-white">{s.pct!.toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Peer comparison table ──────────────────────────────────────────────────────

type PeerSortKey = "name" | "price" | "pe_ratio" | "market_cap" | "roce" | "sales_growth_3yr" | "net_profit" | "div_yield";

function PeersTable({ fund, currentSymbol }: { fund: Fundamentals; currentSymbol: string }) {
  const navigate = useNavigate();
  const [sortKey, setSortKey] = useState<PeerSortKey>("market_cap");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  if (!fund.peers.length) return (
    <p className="text-xs text-gray-600 px-5 py-4">No peer data available from screener.in.</p>
  );

  function handleSort(key: PeerSortKey) {
    if (key === sortKey) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  }

  const sorted = [...fund.peers].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = typeof av === "number" && typeof bv === "number"
      ? av - bv : String(av).localeCompare(String(bv));
    return sortDir === "asc" ? cmp : -cmp;
  });

  function Th({ label, sub, sk, cls = "" }: { label: string; sub?: string; sk: PeerSortKey; cls?: string }) {
    const active = sortKey === sk;
    return (
      <th
        className={`th cursor-pointer select-none hover:text-white transition-colors whitespace-nowrap ${cls}`}
        onClick={() => handleSort(sk)}
      >
        <span className="inline-flex items-center gap-1">
          {label}
          <span className="text-gray-600 text-[10px]">{active ? (sortDir === "asc" ? "▲" : "▼") : "⇅"}</span>
        </span>
        {sub && <><br /><span className="text-gray-600 font-normal">{sub}</span></>}
      </th>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-gray-800/50">
            <th className="th text-left" style={{ minWidth: 160 }}>Company</th>
            <Th label="CMP"           sub="₹"      sk="price"           cls="text-right" />
            <Th label="P/E"           sub="ratio"   sk="pe_ratio"        cls="text-right" />
            <Th label="Mkt Cap"       sub="Rs. Cr"  sk="market_cap"      cls="text-right" />
            <Th label="ROCE"          sub="%"       sk="roce"            cls="text-right" />
            <Th label="Qtr Sales Var" sub="%"       sk="sales_growth_3yr" cls="text-right" />
            <Th label="Net Profit"    sub="Rs. Cr"  sk="net_profit"      cls="text-right" />
            <Th label="Div Yield"     sub="%"       sk="div_yield"       cls="text-right" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((p, i) => {
            const isThis = p.symbol?.toUpperCase() === currentSymbol.toUpperCase();
            return (
              <tr
                key={i}
                className={`hover:bg-gray-800/40 transition-colors ${isThis ? "bg-blue-900/20" : ""} ${p.symbol ? "cursor-pointer" : ""}`}
                onClick={() => p.symbol && navigate(`/stock/${p.symbol}?exchange=NSE`)}
              >
                <td className="td">
                  <div className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-1.5">
                      {isThis && <span className="w-1.5 h-1.5 rounded-full bg-blue-400 inline-block shrink-0" />}
                      <span className={`font-medium ${isThis ? "text-blue-300" : "text-gray-200"}`}>{p.name || "—"}</span>
                    </div>
                    {p.symbol && (
                      <span className="font-mono text-[10px] text-gray-500 ml-3">{p.symbol}</span>
                    )}
                  </div>
                </td>
                <td className="td text-right font-mono text-gray-300">{fmt(p.price, 2, "₹")}</td>
                <td className="td text-right font-mono text-gray-300">{fmt(p.pe_ratio, 1)}</td>
                <td className="td text-right font-mono text-gray-300">
                  {p.market_cap != null
                    ? `₹${p.market_cap.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`
                    : "—"}
                </td>
                <td className={`td text-right font-mono ${
                  p.roce != null ? (p.roce >= 15 ? "text-emerald-400" : p.roce < 10 ? "text-red-400" : "text-gray-300") : "text-gray-600"
                }`}>
                  {fmt(p.roce, 1, "", "%")}
                </td>
                <td className={`td text-right font-mono ${
                  p.sales_growth_3yr != null
                    ? (p.sales_growth_3yr >= 15 ? "text-emerald-400" : p.sales_growth_3yr < 0 ? "text-red-400" : "text-gray-300")
                    : "text-gray-600"
                }`}>
                  {fmt(p.sales_growth_3yr, 1, "", "%")}
                </td>
                <td className="td text-right font-mono text-gray-300">
                  {p.net_profit != null ? `₹${p.net_profit.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "—"}
                </td>
                <td className="td text-right font-mono text-gray-300">{fmt(p.div_yield, 2, "", "%")}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function StockDetailPage() {
  const { symbol } = useParams<{ symbol: string }>();
  const [sp]       = useSearchParams();
  const exchange   = (sp.get("exchange") ?? "NSE").toUpperCase();
  const navigate   = useNavigate();

  const [history, setHistory]             = useState<OHLCVBar[]>([]);
  const [analysis, setAnalysis]           = useState<Analysis | null>(null);
  const [quote, setQuote]                 = useState<import("../api/prices").Quote | null>(null);
  const [fund, setFund]                   = useState<Fundamentals | null>(null);
  const [fundLoading, setFundLoading]     = useState(false);
  const [fundRefreshing, setFundRefreshing] = useState(false);
  const [refreshing, setRefreshing]       = useState(false);
  const [aiError, setAiError]             = useState<string | null>(null);
  const [activeTab, setActiveTab]         = useState<"quarterly" | "pl" | "bs" | "cf" | "ratios">("quarterly");

  // Chart overlay toggles
  const [showSMA20,  setShowSMA20]  = useState(true);
  const [showEMA20,  setShowEMA20]  = useState(true);
  const [showDMA50,  setShowDMA50]  = useState(true);
  const [showDMA200, setShowDMA200] = useState(true);

  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Shared poll loop ──────────────────────────────────────────────────────
  const startPolling = useCallback((newerThan: string | null) => {
    if (!symbol) return;
    const started  = Date.now();
    const MAX_WAIT = 45_000;
    let   attempts = 0;

    const poll = async () => {
      attempts++;
      if (Date.now() - started > MAX_WAIT) {
        setAiError("Analysis is taking longer than expected — try the button again.");
        setRefreshing(false);
        return;
      }
      const a = await analysisApi.getLatest(symbol, exchange).catch(() => null);
      if (a && (!newerThan || a.generated_at > newerThan)) {
        setAnalysis(a);
        setRefreshing(false);
      } else {
        const delay = Math.min(2_000 + attempts * 500, 5_000);
        pollTimer.current = setTimeout(poll, delay);
      }
    };
    pollTimer.current = setTimeout(poll, 4_000);
  }, [symbol, exchange]);

  // Cancel polls on symbol change
  useEffect(() => {
    return () => { if (pollTimer.current) clearTimeout(pollTimer.current); };
  }, [symbol, exchange]);

  // ── On mount: load data + auto-trigger stale analysis ────────────────────
  useEffect(() => {
    if (!symbol) return;
    if (pollTimer.current) clearTimeout(pollTimer.current);

    // Bug 3 fix: single AbortController for all parallel fetches on this symbol.
    // Aborted on cleanup so responses from the previous symbol never reach state.
    const ac = new AbortController();
    const { signal } = ac;

    pricesApi.getHistory(symbol, exchange, 300, signal).then(h => { if (!signal.aborted) setHistory(h); }).catch(() => null);
    pricesApi.getQuote(symbol, exchange, signal).then(q => { if (!signal.aborted) setQuote(q); }).catch(() => null);

    // Load fundamentals
    setFund(null);
    setFundLoading(true);
    fundamentalsApi.get(symbol, exchange, false, signal)
      .then(f => { if (!signal.aborted) setFund(f); })
      .catch(() => { if (!signal.aborted) setFund(null); })
      .finally(() => { if (!signal.aborted) setFundLoading(false); });

    analysisApi.getLatest(symbol, exchange, signal)
      .then(existing => {
        if (signal.aborted) return;
        setAnalysis(existing);
        if (isStale(existing)) {
          setRefreshing(true); setAiError(null);
          analysisApi.refresh(symbol, exchange)
            .then(() => { if (!signal.aborted) startPolling(existing?.generated_at ?? null); })
            .catch(err => { if (!signal.aborted) { setAiError(err.message ?? "Could not start analysis"); setRefreshing(false); } });
        }
      })
      .catch((err: unknown) => {
        if (signal.aborted) return;
        // Bug 1 fix: only auto-trigger a new analysis on a true 404 (no analysis
        // exists yet). A 5xx or network error means the backend is down — do NOT
        // fire a paid Gemini call in response to an outage.
        const is404 = err instanceof ApiError && err.status === 404;
        if (is404) {
          setAnalysis(null);
          setRefreshing(true); setAiError(null);
          analysisApi.refresh(symbol, exchange)
            .then(() => { if (!signal.aborted) startPolling(null); })
            .catch(e => { if (!signal.aborted) { setAiError((e as Error).message ?? "Could not start analysis"); setRefreshing(false); } });
        } else {
          // Backend error — show nothing, let the user click Refresh manually
          setAnalysis(null);
          setRefreshing(false);
        }
      });

    return () => ac.abort();
  }, [symbol, exchange]);

  // ── Fundamentals refresh ──────────────────────────────────────────────────
  async function handleFundRefresh() {
    if (!symbol || fundRefreshing) return;
    setFundRefreshing(true);
    // Clear cache server-side by calling the endpoint with cache-bust query param
    try {
      const fresh = await fundamentalsApi.get(symbol, exchange, true);
      setFund(fresh);
    } catch {
      // silently keep old data
    } finally {
      setFundRefreshing(false);
    }
  }

  // ── Manual refresh button ─────────────────────────────────────────────────
  async function handleRefresh() {
    if (!symbol || refreshing) return;
    if (pollTimer.current) clearTimeout(pollTimer.current);
    setRefreshing(true); setAiError(null);
    try {
      await analysisApi.refresh(symbol, exchange);
      startPolling(analysis?.generated_at ?? null);
    } catch (err: any) {
      setAiError(err.message ?? "Failed to queue analysis");
      setRefreshing(false);
    }
  }

  // ── Chart data with all overlays — memoised so O(n) work only reruns when
  // history changes, not on every poll tick, tab switch, or UI hover.
  const chartData = useMemo(() => {
    const closes = history.map(b => b.close);
    const sma20  = sma(closes, 20);
    const ema20  = ema(closes, 20);
    const dma50  = sma(closes, 50);
    const dma200 = sma(closes, 200);
    return history.map((b, i) => ({
      date:   b.timestamp.slice(0, 10),
      close:  b.close,
      sma20:  sma20[i]  !== null ? parseFloat(sma20[i]!.toFixed(2))  : undefined,
      ema20:  ema20[i]  !== null ? parseFloat(ema20[i]!.toFixed(2))  : undefined,
      dma50:  dma50[i]  !== null ? parseFloat(dma50[i]!.toFixed(2))  : undefined,
      dma200: dma200[i] !== null ? parseFloat(dma200[i]!.toFixed(2)) : undefined,
    }));
  }, [history]);

  // ── Indicator snapshot (from latest analysis) ─────────────────────────────
  const snap = analysis?.indicators_snapshot as Record<string, number | null> | null;
  const ltp  = snap?.current_price;
  const pct1 = snap?.pct_change_1d;

  const hasOverlays  = history.length >= 20;
  const hasDMA50     = history.length >= 50;
  const hasDMA200    = history.length >= 200;

  // ── OPM bar chart data ────────────────────────────────────────────────────
  const opmChartData = (fund?.opm_trend ?? []).map((v, i) => ({
    quarter: `Q${i + 1}`,
    opm: parseFloat(v.toFixed(1)),
  }));

  // ── Active financial table ────────────────────────────────────────────────
  const tabSections: Record<string, import("../api/fundamentals").TableSection | null | undefined> = {
    quarterly: fund?.quarterly_results,
    pl:        fund?.profit_loss,
    bs:        fund?.balance_sheet,
    cf:        fund?.cash_flow,
    ratios:    fund?.key_ratios,
  };
  const activeSection = tabSections[activeTab] ?? null;

  return (
    <div className="p-8 max-w-5xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold text-white">
              {quote?.company_name || symbol}
            </h1>
            <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded font-medium">{exchange}</span>
            {fund?.sector && (
              <span className="text-xs bg-indigo-900/40 text-indigo-300 px-2 py-0.5 rounded border border-indigo-800/50">
                {fund.sector}
              </span>
            )}
            {analysis?.risk_flag && (
              <span className={RISK_BADGE[analysis.risk_flag] ?? "badge-medium"}>
                {analysis.risk_flag.toUpperCase()} RISK
              </span>
            )}
          </div>
          <p className="font-mono text-sm text-gray-500 mt-0.5">
            {symbol}
            {fund?.industry && <span className="ml-2 text-gray-600">· {fund.industry}</span>}
          </p>
          {(quote?.ltp ?? ltp) != null && (
            <p className="text-3xl font-bold text-white mt-2">
              ₹{(quote?.ltp ?? ltp)!.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              {(quote?.pct_change ?? pct1) != null && (
                <span className={`text-base ml-3 ${(quote?.pct_change ?? pct1)! >= 0 ? "gain" : "loss"}`}>
                  {(quote?.pct_change ?? pct1)! >= 0 ? "▲" : "▼"} {Math.abs((quote?.pct_change ?? pct1)!).toFixed(2)}%
                </span>
              )}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(`/alerts?symbol=${symbol}&exchange=${exchange}`)}
            className="btn-ghost flex items-center gap-1.5 text-sm"
            title="Add alert for this stock"
          >
            <Bell size={15} />
            Add Alert
          </button>
          <button
            onClick={() => navigate(`/portfolio?addTrade=${symbol}&exchange=${exchange}`)}
            className="btn-ghost flex items-center gap-1.5 text-sm"
            title="Log a trade for this stock"
          >
            <PlusCircle size={15} />
            Add Trade
          </button>
          <a
            href={`https://www.screener.in/company/${symbol}/`}
            target="_blank" rel="noopener noreferrer"
            className="btn-ghost flex items-center gap-1.5 text-sm"
            title="View on screener.in"
          >
            <ExternalLink size={14} />
            screener.in
          </a>
          <button onClick={handleRefresh} disabled={refreshing} className="btn-primary">
            <RefreshCw size={15} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Generating…" : "Refresh Insight"}
          </button>
        </div>
      </div>

      {/* Price chart */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-400">Price History — 300 days</h2>
          {hasOverlays && (
            <div className="flex items-center gap-2 flex-wrap">
              <OverlayToggle label="SMA-20"  color="#f59e0b" active={showSMA20}  onClick={() => setShowSMA20(v => !v)} />
              <OverlayToggle label="EMA-20"  color="#a78bfa" active={showEMA20}  onClick={() => setShowEMA20(v => !v)} />
              {hasDMA50  && <OverlayToggle label="DMA-50"  color="#fb923c" active={showDMA50}  onClick={() => setShowDMA50(v => !v)} />}
              {hasDMA200 && <OverlayToggle label="DMA-200" color="#f87171" active={showDMA200} onClick={() => setShowDMA200(v => !v)} />}
            </div>
          )}
        </div>

        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#6b7280", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={["auto", "auto"]}
                tick={{ fill: "#6b7280", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => `₹${v.toLocaleString("en-IN")}`}
                width={72}
              />
              <Tooltip
                contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
                labelStyle={{ color: "#9ca3af", fontSize: 11 }}
                formatter={(v: number, name: string) => {
                  const labelMap: Record<string, string> = {
                    close: "Close", sma20: "SMA-20", ema20: "EMA-20",
                    dma50: "DMA-50", dma200: "DMA-200",
                  };
                  return [`₹${v.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`, labelMap[name] ?? name];
                }}
              />
              <Line type="monotone" dataKey="close" stroke="#3b82f6" dot={false} strokeWidth={2} name="close" />
              {hasOverlays && showSMA20 && (
                <Line type="monotone" dataKey="sma20" stroke="#f59e0b" dot={false} strokeWidth={1.5} strokeDasharray="4 2" name="sma20" connectNulls />
              )}
              {hasOverlays && showEMA20 && (
                <Line type="monotone" dataKey="ema20" stroke="#a78bfa" dot={false} strokeWidth={1.5} strokeDasharray="2 2" name="ema20" connectNulls />
              )}
              {hasDMA50 && showDMA50 && (
                <Line type="monotone" dataKey="dma50" stroke="#fb923c" dot={false} strokeWidth={1.5} name="dma50" connectNulls />
              )}
              {hasDMA200 && showDMA200 && (
                <Line type="monotone" dataKey="dma200" stroke="#f87171" dot={false} strokeWidth={2} name="dma200" connectNulls />
              )}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-gray-600">
            <TrendingUp size={28} className="mb-2" />
            <p className="text-sm">No price history yet.</p>
            <p className="text-xs mt-1">Add this symbol to your watchlist — prices populate during market hours.</p>
          </div>
        )}
      </div>

      {/* Technical indicator tiles */}
      {snap && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mb-6">
          <IndicatorTile
            label="RSI (14)"
            value={snap.rsi_14?.toFixed(1) ?? null}
            sub={snap.rsi_14 != null
              ? snap.rsi_14 > 70 ? "Overbought" : snap.rsi_14 < 30 ? "Oversold" : "Neutral"
              : undefined}
          />
          <IndicatorTile
            label="SMA-20"
            value={snap.sma_20 != null ? `₹${snap.sma_20.toLocaleString("en-IN")}` : null}
            sub={snap.price_vs_sma20_pct != null
              ? `${snap.price_vs_sma20_pct > 0 ? "+" : ""}${snap.price_vs_sma20_pct.toFixed(1)}% vs price`
              : undefined}
          />
          <IndicatorTile
            label="DMA-50"
            value={snap.sma_50 != null ? `₹${snap.sma_50.toLocaleString("en-IN")}` : null}
            sub={snap.sma_200 != null && snap.sma_50 != null
              ? snap.sma_50 > snap.sma_200 ? "Golden cross ✓" : "Death cross ✗"
              : undefined}
          />
          <IndicatorTile
            label="DMA-200"
            value={snap.sma_200 != null ? `₹${snap.sma_200.toLocaleString("en-IN")}` : null}
            sub={snap.sma_200 != null && snap.current_price != null
              ? snap.current_price > snap.sma_200 ? "Above (bullish)" : "Below (bearish)"
              : undefined}
          />
          <IndicatorTile label="EMA-20" value={snap.ema_20 != null ? `₹${snap.ema_20.toLocaleString("en-IN")}` : null} />
          <IndicatorTile
            label="5-day Change"
            value={snap.pct_change_5d != null
              ? `${snap.pct_change_5d > 0 ? "+" : ""}${snap.pct_change_5d.toFixed(2)}%`
              : null}
          />
          <IndicatorTile
            label="Volatility (30d ann.)"
            value={snap.realized_volatility_30d != null ? `${snap.realized_volatility_30d.toFixed(1)}%` : null}
          />
        </div>
      )}

      {/* ── FUNDAMENTALS ── */}
      {(fund || fundLoading) && (
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <h2 className="text-base font-semibold text-white">Fundamentals</h2>
            <span className="text-xs text-gray-500">· screener.in</span>
            {(fundLoading || fundRefreshing) && <RefreshCw size={12} className="animate-spin text-gray-500" />}
            {fund && !fundLoading && fund.fetched_at && (() => {
              const ageH = Math.max(0, (Date.now() / 1000 - fund.fetched_at) / 3600);
              const label = ageH < 1 ? "<1h ago" : `${Math.round(ageH)}h ago`;
              return <span className="text-[10px] text-gray-600 ml-1">cached {label}</span>;
            })()}
            {!fundLoading && (
              <button
                onClick={handleFundRefresh}
                disabled={fundRefreshing}
                className="ml-auto btn-ghost text-xs flex items-center gap-1 py-0.5 px-2"
                title="Re-scrape screener.in (24h cache)"
              >
                <RefreshCw size={11} className={fundRefreshing ? "animate-spin" : ""} />
                Refresh
              </button>
            )}
          </div>

          {fund?.error && !fundLoading && (
            <div className="text-xs text-yellow-500/80 bg-yellow-900/10 border border-yellow-800/30 rounded-lg px-4 py-2 mb-3 flex items-center gap-2">
              <AlertTriangle size={12} /> {fund.error}
            </div>
          )}

          {fund && !fund.error && (
            <>
              {/* Key ratios grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mb-4">
                {/* P/E with inline vs-industry comparison */}
                <div className="bg-gray-800/60 rounded-xl px-4 py-3 border border-gray-700/40">
                  <p className="text-xs text-gray-500 mb-1">P/E Ratio</p>
                  <p className={`text-base font-semibold ${
                    fund.pe_ratio != null
                      ? fund.pe_ratio < 15 ? "text-emerald-400"
                      : fund.pe_ratio > 40 ? "text-red-400"
                      : "text-white"
                      : "text-white"
                  }`}>
                    {fund.pe_ratio != null ? `${fund.pe_ratio.toFixed(1)}x` : <span className="text-gray-600 text-sm">—</span>}
                  </p>
                  {/* Industry median comparison */}
                  {fund.industry_pe_median != null && (
                    <p className="text-xs mt-1 flex items-center gap-1">
                      <span className="text-gray-500">Industry median:</span>
                      <span className={`font-semibold ${
                        fund.pe_ratio != null
                          ? fund.pe_ratio > fund.industry_pe_median * 1.2 ? "text-red-400"
                          : fund.pe_ratio < fund.industry_pe_median * 0.8 ? "text-emerald-400"
                          : "text-gray-300"
                          : "text-gray-300"
                      }`}>
                        {fund.industry_pe_median.toFixed(1)}x
                      </span>
                      {fund.pe_ratio != null && (
                        <span className={`text-[10px] px-1 py-0.5 rounded ${
                          fund.pe_ratio > fund.industry_pe_median
                            ? "bg-red-900/30 text-red-400"
                            : "bg-emerald-900/30 text-emerald-400"
                        }`}>
                          {fund.pe_ratio > fund.industry_pe_median ? "Premium" : "Discount"}
                        </span>
                      )}
                    </p>
                  )}
                  {fund.industry_peer_count != null && (
                    <p className="text-[10px] text-gray-600 mt-0.5">
                      vs {fund.industry_peer_count} industry peers
                    </p>
                  )}
                </div>
                <FundTile label="ROCE"          value={fund.roce != null ? `${fund.roce.toFixed(1)}%` : null}
                  highlight={fund.roce != null ? (fund.roce >= 15 ? "good" : fund.roce < 10 ? "bad" : "neutral") : undefined}
                />
                <FundTile label="ROE"           value={fund.roe != null ? `${fund.roe.toFixed(1)}%` : null}
                  highlight={fund.roe != null ? (fund.roe >= 15 ? "good" : fund.roe < 10 ? "bad" : "neutral") : undefined}
                />
                <FundTile label="Debt / Equity" value={fund.debt_to_equity != null ? `${fund.debt_to_equity.toFixed(2)}x` : null}
                  highlight={fund.debt_to_equity != null ? (fund.debt_to_equity < 0.5 ? "good" : fund.debt_to_equity > 1.5 ? "bad" : "neutral") : undefined}
                />
                <FundTile label="Book Value"    value={fund.book_value != null ? `₹${fund.book_value.toLocaleString("en-IN")}` : null} />
                <FundTile label="EPS (TTM)"     value={fund.eps != null ? `₹${fund.eps.toFixed(2)}` : null} />
                <FundTile label="Dividend Yield" value={fund.div_yield != null ? `${fund.div_yield.toFixed(2)}%` : null} />
                <FundTile label="Market Cap"
                  value={fund.market_cap != null ? `₹${fund.market_cap.toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr` : null}
                  sub={fund.market_cap != null
                    ? fund.market_cap >= 20000 ? "Large Cap" : fund.market_cap >= 5000 ? "Mid Cap" : "Small Cap"
                    : undefined}
                  highlight={fund.market_cap != null
                    ? fund.market_cap >= 20000 ? "good" : fund.market_cap >= 5000 ? "neutral" : "bad"
                    : undefined}
                />
              </div>

              {/* Growth rates */}
              {(fund.sales_growth_3yr != null || fund.sales_growth_5yr != null
                || fund.profit_growth_3yr != null || fund.profit_growth_5yr != null) && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                  <FundTile label="Sales CAGR (3yr)"  value={fund.sales_growth_3yr  != null ? `${fund.sales_growth_3yr.toFixed(1)}%`  : null}
                    highlight={fund.sales_growth_3yr  != null ? (fund.sales_growth_3yr  >= 15 ? "good" : fund.sales_growth_3yr  < 0 ? "bad" : "neutral") : undefined} />
                  <FundTile label="Sales CAGR (5yr)"  value={fund.sales_growth_5yr  != null ? `${fund.sales_growth_5yr.toFixed(1)}%`  : null}
                    highlight={fund.sales_growth_5yr  != null ? (fund.sales_growth_5yr  >= 15 ? "good" : fund.sales_growth_5yr  < 0 ? "bad" : "neutral") : undefined} />
                  <FundTile label="Profit CAGR (3yr)" value={fund.profit_growth_3yr != null ? `${fund.profit_growth_3yr.toFixed(1)}%` : null}
                    highlight={fund.profit_growth_3yr != null ? (fund.profit_growth_3yr >= 15 ? "good" : fund.profit_growth_3yr < 0 ? "bad" : "neutral") : undefined} />
                  <FundTile label="Profit CAGR (5yr)" value={fund.profit_growth_5yr != null ? `${fund.profit_growth_5yr.toFixed(1)}%` : null}
                    highlight={fund.profit_growth_5yr != null ? (fund.profit_growth_5yr >= 15 ? "good" : fund.profit_growth_5yr < 0 ? "bad" : "neutral") : undefined} />
                </div>
              )}

              {/* Shareholding + OPM in a 2-col layout */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                {/* Shareholding */}
                {(fund.promoter_pct != null || fund.fii_pct != null) && (
                  <div className="bg-gray-800/40 rounded-xl border border-gray-700/40 px-4 py-4">
                    <p className="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-3">Shareholding Pattern</p>
                    <ShareholdingBar fund={fund} />
                  </div>
                )}

                {/* OPM trend */}
                {opmChartData.length > 0 && (
                  <div className="bg-gray-800/40 rounded-xl border border-gray-700/40 px-4 py-4">
                    <p className="text-xs text-gray-400 font-semibold uppercase tracking-wide mb-3">OPM % (last 4 quarters)</p>
                    <ResponsiveContainer width="100%" height={100}>
                      <BarChart data={opmChartData} margin={{ top: 4, right: 0, bottom: 0, left: -20 }}>
                        <XAxis dataKey="quarter" tick={{ fill: "#6b7280", fontSize: 11 }} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} tickLine={false} axisLine={false} />
                        <Tooltip
                          contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
                          formatter={(v: number) => [`${v}%`, "OPM"]}
                        />
                        <Bar dataKey="opm" fill="#6366f1" radius={[3, 3, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {/* Pros / Cons */}
              {(fund.pros.length > 0 || fund.cons.length > 0) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  {fund.pros.length > 0 && (
                    <div className="bg-emerald-900/10 rounded-xl border border-emerald-800/30 px-4 py-3">
                      <p className="text-xs text-emerald-400 font-semibold uppercase tracking-wide mb-2">Pros</p>
                      <ul className="space-y-1.5">
                        {fund.pros.map((p, i) => (
                          <li key={i} className="text-xs text-gray-300 flex items-start gap-2">
                            <span className="text-emerald-500 mt-0.5">✓</span>{p}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {fund.cons.length > 0 && (
                    <div className="bg-red-900/10 rounded-xl border border-red-800/30 px-4 py-3">
                      <p className="text-xs text-red-400 font-semibold uppercase tracking-wide mb-2">Cons</p>
                      <ul className="space-y-1.5">
                        {fund.cons.map((c, i) => (
                          <li key={i} className="text-xs text-gray-300 flex items-start gap-2">
                            <span className="text-red-500 mt-0.5">✗</span>{c}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Financial data tabs */}
              {(fund.quarterly_results || fund.profit_loss || fund.balance_sheet || fund.cash_flow || fund.key_ratios) && (
                <CollapsibleSection title="Financial Statements" defaultOpen={true}>
                  {/* Tab bar */}
                  <div className="flex gap-0 border-b border-gray-800">
                    {(
                      [
                        ["quarterly", "Quarterly Results"],
                        ["pl",        "P&L"],
                        ["bs",        "Balance Sheet"],
                        ["cf",        "Cash Flow"],
                        ["ratios",    "Key Ratios"],
                      ] as const
                    ).map(([key, label]) => {
                      const hasData = !!tabSections[key];
                      if (!hasData) return null;
                      return (
                        <button
                          key={key}
                          onClick={() => setActiveTab(key)}
                          className={`px-4 py-2.5 text-xs font-medium transition-colors border-b-2 ${
                            activeTab === key
                              ? "border-blue-500 text-blue-400"
                              : "border-transparent text-gray-500 hover:text-white"
                          }`}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                  {activeSection
                    ? <DataTable section={activeSection} />
                    : <p className="text-xs text-gray-600 p-4">No data for this section.</p>
                  }
                </CollapsibleSection>
              )}

              {/* Peer comparison */}
              <CollapsibleSection title={`Peer Comparison (${fund.peers.length} companies)`} defaultOpen={true}>
                <PeersTable fund={fund} currentSymbol={symbol ?? ""} />
              </CollapsibleSection>
            </>
          )}
        </div>
      )}

      {/* AI Insight panel */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">AI Insight</h2>
          {analysis?.generated_at && !refreshing && (
            <span className="text-xs text-gray-500">
              {new Date(analysis.generated_at).toLocaleDateString("en-IN", {
                day: "2-digit", month: "short", year: "numeric",
              })}
            </span>
          )}
          {refreshing && (
            <span className="text-xs text-gray-500 flex items-center gap-1.5">
              <RefreshCw size={11} className="animate-spin" /> Analysing…
            </span>
          )}
        </div>

        {aiError && (
          <div className="flex items-center gap-2 text-red-400 text-sm mb-4 bg-red-900/20 rounded-lg px-3 py-2">
            <AlertTriangle size={14} /> {aiError}
          </div>
        )}

        {analysis?.structured_output ? (
          <div>
            {analysis.structured_output.recommendation && (
              <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold mb-4 ${REC_STYLE[analysis.structured_output.recommendation] ?? REC_STYLE.HOLD}`}>
                <span>{REC_ICON[analysis.structured_output.recommendation]}</span>
                {analysis.structured_output.recommendation}
              </div>
            )}

            <p className="text-gray-200 text-sm leading-relaxed mb-3">
              {analysis.structured_output.summary}
            </p>

            {analysis.structured_output.rationale && (
              <div className="bg-gray-800/50 rounded-lg px-4 py-3 mb-4">
                <p className="text-xs text-gray-400 uppercase tracking-wide mb-1 font-semibold">Why this recommendation</p>
                <p className="text-gray-300 text-sm leading-relaxed">{analysis.structured_output.rationale}</p>
              </div>
            )}

            <div className="border-t border-gray-800 pt-4 space-y-2">
              <p className="text-xs text-yellow-500/80 flex gap-2 items-start">
                <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                {analysis.structured_output.caveats}
              </p>
              <p className="text-xs text-gray-600">{analysis.structured_output.disclaimer}</p>
            </div>
          </div>
        ) : !refreshing ? (
          <div className="text-center py-8">
            <p className="text-gray-500 text-sm">No analysis yet.</p>
            <p className="text-gray-600 text-xs mt-1">Click "Refresh Insight" above to generate one.</p>
          </div>
        ) : (
          <div className="space-y-2 animate-pulse">
            <div className="h-3.5 bg-gray-800 rounded w-full" />
            <div className="h-3.5 bg-gray-800 rounded w-5/6" />
            <div className="h-3.5 bg-gray-800 rounded w-4/6" />
          </div>
        )}
      </div>
    </div>
  );
}
