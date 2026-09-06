import { useEffect, useRef, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import { tradesApi, TradeOut } from "../api/trades";
import { watchlistApi, SymbolSearchResult } from "../api/watchlist";
import { TrendingUp, TrendingDown, Minus, Plus, X, Search, Trash2, ChevronDown, ChevronUp, ChevronsUpDown, RefreshCw, AlertTriangle, BrainCircuit } from "lucide-react";
import { useSortFilter } from "../hooks/useSortFilter";

// ── Portfolio analysis types ──────────────────────────────────────────────────

interface PositionAdvice {
  symbol: string;
  action: "BUY_MORE" | "HOLD" | "TRIM" | "EXIT";
  reasoning: string;
}

interface PortfolioAnalysis {
  status: string;
  generated_at: string | null;
  overall_health: "strong" | "moderate" | "weak" | "critical" | null;
  summary: string | null;
  positions: PositionAdvice[] | null;
  rebalance_notes: string | null;
  risk_notes: string | null;
  disclaimer: string | null;
}

const HEALTH_STYLE: Record<string, string> = {
  strong:   "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  moderate: "text-blue-400 bg-blue-500/10 border-blue-500/30",
  weak:     "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
  critical: "text-red-400 bg-red-500/10 border-red-500/30",
};

const ACTION_STYLE: Record<string, string> = {
  BUY_MORE: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
  HOLD:     "bg-blue-500/15 text-blue-400 border border-blue-500/30",
  TRIM:     "bg-yellow-500/15 text-yellow-400 border border-yellow-500/30",
  EXIT:     "bg-red-500/15 text-red-400 border border-red-500/30",
};

const ACTION_ICON: Record<string, string> = {
  BUY_MORE: "▲▲", HOLD: "◆", TRIM: "▼", EXIT: "✕",
};

interface PortfolioRow {
  id: number; symbol: string; exchange: string; company_name: string | null;
  total_quantity: number; avg_buy_price: number; total_invested: number;
  current_price: number | null; current_value: number | null;
  unrealized_pnl: number | null; unrealized_pnl_pct: number | null;
}

function inr(n: number | null, showSign = false) {
  if (n == null) return <span className="text-gray-600">—</span>;
  const sign = showSign && n > 0 ? "+" : n < 0 ? "-" : "";
  return `${sign}₹${Math.abs(n).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
}

// ── Sortable header cell ───────────────────────────────────────────────────────

function SortTh({
  label, sortKey, current, dir, onSort, className = "",
}: {
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
          : <ChevronsUpDown size={12} className="text-gray-600" />}
      </span>
    </th>
  );
}

// ── Add Transaction Modal ──────────────────────────────────────────────────────

interface ModalProps {
  onClose: () => void;
  onAdded: () => void;
  prefillSymbol?: string;
  prefillExchange?: string;
}

function AddTradeModal({ onClose, onAdded, prefillSymbol = "", prefillExchange = "NSE" }: ModalProps) {
  const today = new Date().toISOString().slice(0, 10);

  const [query, setQuery]             = useState(prefillSymbol);
  const [selSymbol, setSelSymbol]     = useState(prefillSymbol);
  const [selName, setSelName]         = useState("");
  const [selExchange, setSelExchange] = useState(prefillExchange);
  const [suggestions, setSuggestions] = useState<SymbolSearchResult[]>([]);
  const [showSug, setShowSug]         = useState(false);
  const [fetchingPrice, setFetchingPrice] = useState(false);
  const debounce                      = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dropRef                       = useRef<HTMLDivElement>(null);

  const [tradeType, setTradeType]   = useState<"BUY" | "SELL">("BUY");
  const [date, setDate]             = useState(today);
  const [qty, setQty]               = useState("");
  const [price, setPrice]           = useState("");
  const [brokerage, setBrokerage]   = useState("0");
  const [notes, setNotes]           = useState("");
  const [saving, setSaving]         = useState(false);
  const [error, setError]           = useState<string | null>(null);

  // When opened with a pre-filled symbol, auto-fetch its live price
  useEffect(() => {
    if (!prefillSymbol) return;
    setFetchingPrice(true);
    apiFetch<{ ltp: number }>(`/prices/${prefillSymbol}?exchange=${prefillExchange}`)
      .then(q => { if (q?.ltp) setPrice(q.ltp.toFixed(2)); })
      .catch(() => {})
      .finally(() => setFetchingPrice(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function h(e: MouseEvent) {
      if (dropRef.current && !dropRef.current.contains(e.target as Node))
        setShowSug(false);
    }
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  function handleQueryChange(v: string) {
    setQuery(v); setSelSymbol(""); setSelName("");
    if (debounce.current) clearTimeout(debounce.current);
    if (!v.trim()) { setSuggestions([]); setShowSug(false); return; }
    debounce.current = setTimeout(async () => {
      try {
        const r = await watchlistApi.search(v.trim());
        setSuggestions(r); setShowSug(r.length > 0);
      } catch { setSuggestions([]); setShowSug(false); }
    }, 250);
  }

  async function handleSelect(s: SymbolSearchResult) {
    setQuery(`${s.symbol} — ${s.company_name}`);
    setSelSymbol(s.symbol); setSelName(s.company_name);
    setSelExchange(s.exchange);
    setShowSug(false);

    // Pre-fill price with the live LTP
    setFetchingPrice(true);
    try {
      const { apiFetch } = await import("../api/client");
      const q = await apiFetch<{ ltp: number }>(`/prices/${s.symbol}?exchange=${s.exchange}`);
      if (q?.ltp) setPrice(q.ltp.toFixed(2));
    } catch {
      // Non-fatal — user can type price manually
    } finally {
      setFetchingPrice(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const sym = (selSymbol || query).trim().toUpperCase();
    if (!sym || !qty || !price) { setError("Symbol, quantity and price are required."); return; }
    setSaving(true); setError(null);
    try {
      await tradesApi.add({
        trade_date:   date,
        symbol:       sym,
        exchange:     selExchange,
        company_name: selName || undefined,
        trade_type:   tradeType,
        quantity:     parseInt(qty),
        price:        parseFloat(price),
        brokerage:    parseFloat(brokerage) || 0,
        notes:        notes || undefined,
      });
      onAdded();
      onClose();
    } catch (err: any) {
      setError(err.message ?? "Failed to save trade");
    } finally {
      setSaving(false);
    }
  }

  const totalValue = qty && price
    ? (parseInt(qty) || 0) * (parseFloat(price) || 0) + (parseFloat(brokerage) || 0)
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl w-full max-w-lg mx-4">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h2 className="text-base font-semibold text-white">Add Transaction</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">

          {/* BUY / SELL toggle */}
          <div className="flex rounded-lg overflow-hidden border border-gray-700 w-fit">
            {(["BUY", "SELL"] as const).map(t => (
              <button
                key={t} type="button"
                onClick={() => setTradeType(t)}
                className={`px-6 py-2 text-sm font-semibold transition-colors ${
                  tradeType === t
                    ? t === "BUY"
                      ? "bg-emerald-600 text-white"
                      : "bg-red-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:text-white"
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Symbol search */}
          <div ref={dropRef} className="relative">
            <label className="block text-xs text-gray-400 mb-1.5">Symbol</label>
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                className="input pl-8"
                placeholder="Search symbol or company name…"
                value={query}
                onChange={e => handleQueryChange(e.target.value)}
                onFocus={() => suggestions.length > 0 && setShowSug(true)}
                autoComplete="off"
              />
            </div>
            {showSug && (
              <ul className="absolute z-50 left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-hidden max-h-52 overflow-y-auto">
                {suggestions.map(s => (
                  <li
                    key={s.symbol}
                    onMouseDown={() => handleSelect(s)}
                    className="flex items-center justify-between px-4 py-2.5 hover:bg-gray-800 cursor-pointer"
                  >
                    <div>
                      <span className="font-mono font-semibold text-white text-sm">{s.symbol}</span>
                      <span className="ml-2 text-gray-400 text-sm">{s.company_name}</span>
                    </div>
                    <span className="text-xs bg-gray-800 text-gray-500 px-1.5 py-px rounded ml-3 shrink-0">{s.exchange}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Date + Exchange row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Trade Date</label>
              <input type="date" className="input" value={date}
                onChange={e => setDate(e.target.value)} max={today} />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Exchange</label>
              <select className="select w-full" value={selExchange}
                onChange={e => setSelExchange(e.target.value)}>
                <option>NSE</option>
                <option>BSE</option>
              </select>
            </div>
          </div>

          {/* Qty + Price + Brokerage row */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Quantity</label>
              <input type="number" min="1" step="1" className="input" placeholder="100"
                value={qty} onChange={e => setQty(e.target.value)} />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">
                Price (₹)
                {fetchingPrice && <span className="ml-1 text-gray-600 text-xs">fetching…</span>}
              </label>
              <input type="number" min="0.01" step="0.01"
                className={`input ${fetchingPrice ? "opacity-50" : ""}`}
                placeholder="1250.00"
                value={price}
                onChange={e => setPrice(e.target.value)}
                disabled={fetchingPrice}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Brokerage (₹)</label>
              <input type="number" min="0" step="0.01" className="input" placeholder="0"
                value={brokerage} onChange={e => setBrokerage(e.target.value)} />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Notes <span className="text-gray-600">(optional)</span></label>
            <input className="input" placeholder="e.g. SIP, earnings play…"
              value={notes} onChange={e => setNotes(e.target.value)} />
          </div>

          {/* Total preview */}
          {totalValue != null && (
            <div className={`flex items-center justify-between px-4 py-2.5 rounded-lg text-sm ${
              tradeType === "BUY" ? "bg-emerald-900/20 border border-emerald-800/40" : "bg-red-900/20 border border-red-800/40"
            }`}>
              <span className="text-gray-400">Total {tradeType === "BUY" ? "outflow" : "inflow"}</span>
              <span className={`font-mono font-semibold ${tradeType === "BUY" ? "text-emerald-400" : "text-red-400"}`}>
                ₹{totalValue.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </span>
            </div>
          )}

          {error && (
            <p className="text-red-400 text-sm bg-red-900/20 border border-red-800/40 rounded-lg px-3 py-2">{error}</p>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 text-sm font-medium transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={saving}
              className={`flex-1 px-4 py-2.5 rounded-lg text-white text-sm font-semibold transition-colors disabled:opacity-50 ${
                tradeType === "BUY" ? "bg-emerald-600 hover:bg-emerald-500" : "bg-red-600 hover:bg-red-500"
              }`}>
              {saving ? "Saving…" : `Record ${tradeType}`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Trade history row ──────────────────────────────────────────────────────────

function TradeRow({ trade, onDelete }: { trade: TradeOut; onDelete: (id: number) => void }) {
  const isBuy = trade.trade_type === "BUY";
  const rpnl  = trade.realized_pnl;
  return (
    <tr className="hover:bg-gray-800/30 transition-colors group">
      <td className="td text-gray-400 text-sm">{trade.trade_date}</td>
      <td className="td text-center">
        <span className={`inline-block text-xs font-semibold px-2 py-0.5 rounded ${isBuy ? "bg-emerald-900/40 text-emerald-400" : "bg-red-900/40 text-red-400"}`}>
          {trade.trade_type}
        </span>
      </td>
      <td className="td">
        <div className="flex flex-col">
          <span className="font-semibold text-white text-sm">{trade.company_name || trade.symbol}</span>
          {trade.company_name && <span className="font-mono text-xs text-gray-500 mt-0.5">{trade.symbol}</span>}
        </div>
      </td>
      <td className="td text-right text-gray-300">{trade.quantity}</td>
      <td className="td text-right font-mono text-gray-300">₹{trade.price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
      <td className="td text-right font-mono text-gray-500">₹{trade.brokerage.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
      <td className="td text-right font-mono">
        {!isBuy && rpnl != null
          ? <span className={rpnl >= 0 ? "gain" : "loss"}>
              {rpnl >= 0 ? "+" : ""}₹{Math.abs(rpnl).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </span>
          : <span className="text-gray-700">—</span>}
      </td>
      <td className="td text-center w-10">
        <button
          onClick={() => onDelete(trade.id)}
          className="text-gray-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
        >
          <Trash2 size={13} />
        </button>
      </td>
    </tr>
  );
}

// ── Main Portfolio Page ────────────────────────────────────────────────────────

// ── AI Portfolio Review card ──────────────────────────────────────────────────

function PortfolioReviewCard({ hasHoldings }: { hasHoldings: boolean }) {
  const [result, setResult]     = useState<PortfolioAnalysis | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);

  async function runAnalysis() {
    setLoading(true); setError(null);
    try {
      const data = await apiFetch<PortfolioAnalysis>("/trades/portfolio/analyse", { method: "POST" });
      setResult(data);
      if (data.status !== "ok") setError(data.summary ?? "Analysis failed");
    } catch (err: any) {
      setError(err.message ?? "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card p-0 overflow-hidden mb-6">
      {/* Header row */}
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <BrainCircuit size={16} className="text-violet-400" />
          <span className="text-sm font-semibold text-white">AI Portfolio Review</span>
          {result?.overall_health && (
            <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${HEALTH_STYLE[result.overall_health]}`}>
              {result.overall_health.toUpperCase()}
            </span>
          )}
          {result?.generated_at && (
            <span className="text-xs text-gray-500 ml-1">
              {new Date(result.generated_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={runAnalysis}
            disabled={loading || !hasHoldings}
            className="btn-primary text-xs py-1.5 px-3 disabled:opacity-40"
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
            {loading ? "Analysing…" : result ? "Re-analyse" : "Analyse Portfolio"}
          </button>
          {result && (
            <button onClick={() => setExpanded(v => !v)} className="text-gray-500 hover:text-white transition-colors">
              {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="px-6 pb-4 flex items-center gap-2 text-red-400 text-sm">
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="px-6 pb-5 space-y-2 animate-pulse border-t border-gray-800 pt-4">
          <div className="h-3 bg-gray-800 rounded w-full" />
          <div className="h-3 bg-gray-800 rounded w-5/6" />
          <div className="h-3 bg-gray-800 rounded w-4/6" />
        </div>
      )}

      {/* Results */}
      {result?.status === "ok" && !loading && expanded && (
        <div className="border-t border-gray-800 px-6 py-5 space-y-5">

          {/* Summary */}
          <p className="text-gray-200 text-sm leading-relaxed">{result.summary}</p>

          {/* Per-position actions */}
          {result.positions && result.positions.length > 0 && (
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold mb-3">Position Advice</p>
              <div className="space-y-2">
                {result.positions.map(p => (
                  <div key={p.symbol} className="flex items-start gap-3 bg-gray-800/40 rounded-lg px-4 py-3">
                    <span className={`shrink-0 text-xs font-bold px-2 py-1 rounded ${ACTION_STYLE[p.action] ?? ACTION_STYLE.HOLD}`}>
                      {ACTION_ICON[p.action]} {p.action.replace("_", " ")}
                    </span>
                    <div className="min-w-0">
                      <span className="font-mono font-semibold text-white text-sm">{p.symbol}</span>
                      <p className="text-gray-400 text-xs mt-0.5 leading-relaxed">{p.reasoning}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Rebalance + risk notes */}
          <div className="grid grid-cols-2 gap-4">
            {result.rebalance_notes && (
              <div className="bg-gray-800/40 rounded-lg px-4 py-3">
                <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold mb-1">Diversification</p>
                <p className="text-gray-300 text-xs leading-relaxed">{result.rebalance_notes}</p>
              </div>
            )}
            {result.risk_notes && (
              <div className="bg-gray-800/40 rounded-lg px-4 py-3">
                <p className="text-xs text-gray-400 uppercase tracking-wide font-semibold mb-1">Risk Watch</p>
                <p className="text-gray-300 text-xs leading-relaxed">{result.risk_notes}</p>
              </div>
            )}
          </div>

          {result.disclaimer && (
            <p className="text-xs text-gray-600 border-t border-gray-800 pt-3">{result.disclaimer}</p>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && !error && (
        <div className="border-t border-gray-800 px-6 py-8 text-center">
          <p className="text-gray-500 text-sm">
            {hasHoldings
              ? "Click \"Analyse Portfolio\" to get AI-powered buy/sell advice across all your holdings."
              : "Add transactions first, then run the portfolio analysis."}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Main Portfolio Page ────────────────────────────────────────────────────────

export default function PortfolioPage() {
  const [sp]     = useSearchParams();
  const navigate = useNavigate();
  const prefillSymbol   = sp.get("addTrade")?.toUpperCase() ?? "";
  const prefillExchange = sp.get("exchange")?.toUpperCase() ?? "NSE";

  const [rows, setRows]           = useState<PortfolioRow[]>([]);
  const [trades, setTrades]       = useState<TradeOut[]>([]);
  // Auto-open modal when navigated from StockDetail with ?addTrade=SYMBOL
  const [showModal, setShowModal] = useState(!!prefillSymbol);
  const [showTrades, setShowTrades] = useState(true);

  function loadPortfolio() {
    apiFetch<PortfolioRow[]>("/trades/portfolio").then(setRows).catch(console.error);
  }
  function loadTrades() {
    tradesApi.list().then(setTrades).catch(console.error);
  }

  useEffect(() => {
    loadPortfolio();
    loadTrades();
  }, []);

  async function handleDeleteTrade(id: number) {
    await tradesApi.remove(id);
    loadTrades();
    loadPortfolio();
  }

  const totalInvested = rows.reduce((s, r) => s + r.total_invested, 0);
  const totalValue    = rows.reduce((s, r) => s + (r.current_value ?? r.total_invested), 0);
  const totalPnl      = totalValue - totalInvested;
  const totalPct      = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0;
  const gainers       = rows.filter(r => (r.unrealized_pnl ?? 0) > 0).length;
  const losers        = rows.filter(r => (r.unrealized_pnl ?? 0) < 0).length;

  const summaryCards = [
    { label: "Invested",      value: `₹${totalInvested.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`, sub: `${rows.length} holdings`,   color: "text-white" },
    { label: "Current Value", value: `₹${totalValue.toLocaleString("en-IN",    { minimumFractionDigits: 2 })}`, sub: "Mark to market",             color: "text-white" },
    { label: "Unrealized P&L",value: `${totalPnl >= 0 ? "+" : ""}₹${Math.abs(totalPnl).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,   sub: `${totalPct >= 0 ? "+" : ""}${totalPct.toFixed(2)}%`, color: totalPnl >= 0 ? "gain" : "loss" },
    { label: "Gainers / Losers", value: `${gainers} / ${losers}`, sub: `${rows.length - gainers - losers} neutral`, color: "text-white" },
  ];

  // ── Holdings sort + filter ────────────────────────────────────────────────
  const [holdingsFilter, setHoldingsFilter] = useState("");

  const holdingsSort = useSortFilter(rows, {
    textKeys: ["symbol", "company_name"],
    getValue: (r, key) => {
      switch (key) {
        case "script":        return r.company_name ?? r.symbol;
        case "qty":           return r.total_quantity;
        case "avg_price":     return r.avg_buy_price;
        case "invested":      return r.total_invested;
        case "ltp":           return r.current_price ?? -Infinity;
        case "current_value": return r.current_value ?? -Infinity;
        case "pnl":           return r.unrealized_pnl ?? -Infinity;
        case "pnl_pct":       return r.unrealized_pnl_pct ?? -Infinity;
        default:              return "";
      }
    },
    defaultSortKey: "",
  });

  const displayedHoldings = holdingsFilter.trim()
    ? holdingsSort.filtered.filter(r =>
        `${r.symbol} ${r.company_name ?? ""}`.toLowerCase().includes(holdingsFilter.trim().toLowerCase())
      )
    : holdingsSort.filtered;

  // ── Transaction history sort + filter ────────────────────────────────────
  const [tradesFilter, setTradesFilter] = useState("");

  const tradesSort = useSortFilter(trades, {
    textKeys: ["symbol", "company_name"],
    getValue: (t, key) => {
      switch (key) {
        case "date":         return t.trade_date;
        case "type":         return t.trade_type;
        case "script":       return t.company_name ?? t.symbol;
        case "qty":          return t.quantity;
        case "price":        return t.price;
        case "brokerage":    return t.brokerage;
        case "realized_pnl": return t.realized_pnl ?? -Infinity;
        default:             return "";
      }
    },
    defaultSortKey: "date",
    defaultSortDir: "desc",
  });

  const displayedTrades = tradesFilter.trim()
    ? tradesSort.filtered.filter(t =>
        `${t.symbol} ${t.company_name ?? ""} ${t.trade_type}`.toLowerCase().includes(tradesFilter.trim().toLowerCase())
      )
    : tradesSort.filtered;

  return (
    <div className="p-8 max-w-6xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Portfolio</h1>
          <p className="text-gray-400 text-sm mt-1">Current holdings and unrealized P&amp;L</p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary">
          <Plus size={15} />
          Add Transaction
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {summaryCards.map(c => (
          <div key={c.label} className="card">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{c.label}</p>
            <p className={`text-xl font-bold mt-2 ${c.color}`}>{c.value}</p>
            <p className="text-xs text-gray-500 mt-1">{c.sub}</p>
          </div>
        ))}
      </div>

      {/* AI Portfolio Review */}
      <PortfolioReviewCard hasHoldings={rows.length > 0} />

      {/* Holdings filter */}
      {rows.length > 1 && (
        <div className="mb-3 relative max-w-xs">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input pl-8 text-sm py-2"
            placeholder="Filter holdings…"
            value={holdingsFilter}
            onChange={e => setHoldingsFilter(e.target.value)}
          />
        </div>
      )}

      {/* Holdings table */}
      <div className="card p-0 overflow-hidden mb-6">
        <table className="w-full">
          <thead className="bg-gray-800/50">
            <tr>
              <SortTh label="Script"        sortKey="script"        current={holdingsSort.sortKey} dir={holdingsSort.sortDir} onSort={holdingsSort.setSort} />
              <SortTh label="Qty"           sortKey="qty"           current={holdingsSort.sortKey} dir={holdingsSort.sortDir} onSort={holdingsSort.setSort} className="text-right" />
              <SortTh label="Avg Price"     sortKey="avg_price"     current={holdingsSort.sortKey} dir={holdingsSort.sortDir} onSort={holdingsSort.setSort} className="text-right" />
              <SortTh label="Invested"      sortKey="invested"      current={holdingsSort.sortKey} dir={holdingsSort.sortDir} onSort={holdingsSort.setSort} className="text-right" />
              <SortTh label="LTP"           sortKey="ltp"           current={holdingsSort.sortKey} dir={holdingsSort.sortDir} onSort={holdingsSort.setSort} className="text-right" />
              <SortTh label="Current Value" sortKey="current_value" current={holdingsSort.sortKey} dir={holdingsSort.sortDir} onSort={holdingsSort.setSort} className="text-right" />
              <SortTh label="P&amp;L"       sortKey="pnl"           current={holdingsSort.sortKey} dir={holdingsSort.sortDir} onSort={holdingsSort.setSort} className="text-right" />
              <SortTh label="P&amp;L %"     sortKey="pnl_pct"       current={holdingsSort.sortKey} dir={holdingsSort.sortDir} onSort={holdingsSort.setSort} className="text-right" />
            </tr>
          </thead>
          <tbody>
            {displayedHoldings.length === 0 && (
              <tr>
                <td colSpan={8} className="td text-center text-gray-500 py-16">
                  {rows.length === 0
                    ? <>No holdings yet — click <span className="text-white font-medium">Add Transaction</span> to record your first trade.</>
                    : "No results match your filter."}
                </td>
              </tr>
            )}
            {displayedHoldings.map(r => {
              const pnl  = r.unrealized_pnl;
              const pct  = r.unrealized_pnl_pct;
              const up   = (pnl ?? 0) >= 0;
              const Icon = pnl == null ? Minus : up ? TrendingUp : TrendingDown;
              return (
                <tr
                  key={r.id}
                  onClick={() => navigate(`/stock/${r.symbol}?exchange=${r.exchange}`)}
                  className="hover:bg-gray-800/40 cursor-pointer transition-colors"
                >
                  <td className="td">
                    <div className="flex flex-col">
                      <span className="font-semibold text-white">{r.company_name || r.symbol}</span>
                      <span className="flex items-center gap-1.5 mt-0.5">
                        <span className="font-mono text-xs text-gray-500">{r.symbol}</span>
                        <span className="text-xs bg-gray-800 text-gray-500 px-1.5 py-px rounded">{r.exchange}</span>
                      </span>
                    </div>
                  </td>
                  <td className="td text-right text-gray-300">{r.total_quantity}</td>
                  <td className="td text-right font-mono text-gray-300">₹{r.avg_buy_price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                  <td className="td text-right font-mono text-gray-300">₹{r.total_invested.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                  <td className="td text-right font-mono text-white">{r.current_price != null ? `₹${r.current_price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : <span className="text-gray-600">—</span>}</td>
                  <td className="td text-right font-mono text-white">{r.current_value != null ? `₹${r.current_value.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : <span className="text-gray-600">—</span>}</td>
                  <td className={`td text-right font-mono ${pnl == null ? "text-gray-600" : up ? "gain" : "loss"}`}>
                    <span className="flex items-center justify-end gap-1">
                      <Icon size={13} />
                      {pnl != null ? `${up ? "+" : "-"}₹${Math.abs(pnl).toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "—"}
                    </span>
                  </td>
                  <td className={`td text-right font-mono ${pct == null ? "text-gray-600" : up ? "gain" : "loss"}`}>
                    {pct != null ? `${up ? "+" : ""}${pct.toFixed(2)}%` : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Transaction history collapsible */}
      {trades.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4">
            <button
              onClick={() => setShowTrades(v => !v)}
              className="flex items-center gap-2 hover:text-white transition-colors"
            >
              <span className="text-sm font-semibold text-white">
                Transaction History <span className="text-gray-500 font-normal ml-1">({trades.length})</span>
              </span>
              {showTrades ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
            </button>

            {/* History filter — only visible when expanded */}
            {showTrades && trades.length > 1 && (
              <div className="relative">
                <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  className="input pl-8 text-sm py-1.5 w-48"
                  placeholder="Filter…"
                  value={tradesFilter}
                  onChange={e => setTradesFilter(e.target.value)}
                />
              </div>
            )}
          </div>

          {showTrades && (
            <table className="w-full border-t border-gray-800">
              <thead className="bg-gray-800/50">
                <tr>
                  <SortTh label="Date"        sortKey="date"        current={tradesSort.sortKey} dir={tradesSort.sortDir} onSort={tradesSort.setSort} />
                  <SortTh label="Type"        sortKey="type"        current={tradesSort.sortKey} dir={tradesSort.sortDir} onSort={tradesSort.setSort} className="text-center" />
                  <SortTh label="Script"      sortKey="script"      current={tradesSort.sortKey} dir={tradesSort.sortDir} onSort={tradesSort.setSort} />
                  <SortTh label="Qty"         sortKey="qty"         current={tradesSort.sortKey} dir={tradesSort.sortDir} onSort={tradesSort.setSort} className="text-right" />
                  <SortTh label="Price"       sortKey="price"       current={tradesSort.sortKey} dir={tradesSort.sortDir} onSort={tradesSort.setSort} className="text-right" />
                  <SortTh label="Brokerage"   sortKey="brokerage"   current={tradesSort.sortKey} dir={tradesSort.sortDir} onSort={tradesSort.setSort} className="text-right" />
                  <SortTh label="Realized P&L" sortKey="realized_pnl" current={tradesSort.sortKey} dir={tradesSort.sortDir} onSort={tradesSort.setSort} className="text-right" />
                  <th className="th w-10"></th>
                </tr>
              </thead>
              <tbody>
                {displayedTrades.length === 0 && (
                  <tr>
                    <td colSpan={8} className="td text-center text-gray-500 py-8">
                      No transactions match your filter.
                    </td>
                  </tr>
                )}
                {displayedTrades.map(t => (
                  <TradeRow key={t.id} trade={t} onDelete={handleDeleteTrade} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <AddTradeModal
          onClose={() => setShowModal(false)}
          onAdded={() => { loadPortfolio(); loadTrades(); }}
          prefillSymbol={prefillSymbol}
          prefillExchange={prefillExchange}
        />
      )}
    </div>
  );
}
