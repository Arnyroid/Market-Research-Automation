import { useEffect, useRef, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import {
  PieChart as RPieChart, Pie, Cell, Tooltip as RTooltip, ResponsiveContainer, Legend,
  BarChart as RBarChart, Bar, XAxis, YAxis, CartesianGrid, LabelList,
} from "recharts";
import { apiFetch } from "../api/client";
import { tradesApi, TradeOut } from "../api/trades";
import { watchlistApi, SymbolSearchResult } from "../api/watchlist";
import { corporateActionsApi, CorporateActionOut } from "../api/corporateActions";
import { TrendingUp, TrendingDown, Minus, Plus, X, Search, Trash2, ChevronDown, ChevronUp, ChevronsUpDown, RefreshCw, AlertTriangle, BrainCircuit, Download } from "lucide-react";
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
  cap_tier: "large" | "mid" | "small" | null;
}

// ── Chart colours ─────────────────────────────────────────────────────────────

const CAP_COLORS: Record<string, string> = {
  large:   "#3b82f6",   // blue
  mid:     "#8b5cf6",   // purple
  small:   "#f97316",   // orange
  unknown: "#4b5563",   // gray
};

const HOLDING_PALETTE = [
  "#3b82f6","#8b5cf6","#06b6d4","#10b981","#f59e0b",
  "#f97316","#ef4444","#a78bfa","#34d399","#fbbf24",
  "#60a5fa","#c084fc",
];

// ── Portfolio analytics component ─────────────────────────────────────────────

interface TierStats {
  tier: string;
  label: string;
  count: number;
  invested: number;
  currentValue: number;
  pnl: number;
  pnlPct: number;
}

type AnalyticsTab = "cap_alloc" | "industry_alloc" | "tier_vs_current" | "pnl_pct";
const ANALYTICS_TABS: { key: AnalyticsTab; label: string }[] = [
  { key: "cap_alloc",       label: "Cap Allocation" },
  { key: "industry_alloc",  label: "Industry Allocation" },
  { key: "tier_vs_current", label: "Invested vs Current" },
  { key: "pnl_pct",         label: "P&L %" },
];

function PortfolioAnalyticsPanel({
  rows,
  fundMap,
}: {
  rows: PortfolioRow[];
  fundMap: Record<string, { industry: string | null; sector: string | null }>;
}) {
  // #7 — collapsed by default when < 5 holdings
  const [open, setOpen] = useState(rows.length >= 5);
  const [activeTab, setActiveTab] = useState<AnalyticsTab>("cap_alloc");
  if (rows.length === 0) return null;

  // ── Per-tier aggregates ───────────────────────────────────────────────────
  const tierOrder: Array<"large" | "mid" | "small" | "unknown"> = ["large", "mid", "small", "unknown"];
  const tierLabels: Record<string, string> = { large: "Large Cap", mid: "Mid Cap", small: "Small Cap", unknown: "Unknown" };

  const tierStats: TierStats[] = tierOrder
    .map(tier => {
      const subset = rows.filter(r => (r.cap_tier ?? "unknown") === tier);
      if (!subset.length) return null;
      const invested = subset.reduce((s, r) => s + r.total_invested, 0);
      const cur      = subset.reduce((s, r) => s + (r.current_value ?? r.total_invested), 0);
      const pnl      = cur - invested;
      return {
        tier,
        label: tierLabels[tier],
        count: subset.length,
        invested,
        currentValue: cur,
        pnl,
        pnlPct: invested > 0 ? (pnl / invested) * 100 : 0,
      } as TierStats;
    })
    .filter(Boolean) as TierStats[];

  const totalInvested = rows.reduce((s, r) => s + r.total_invested, 0);
  const totalValue    = rows.reduce((s, r) => s + (r.current_value ?? r.total_invested), 0);

  // ── Pie: allocation by invested amount ───────────────────────────────────
  const allocationData = tierStats.map(t => ({
    name:  t.label,
    value: parseFloat(t.invested.toFixed(2)),
    color: CAP_COLORS[t.tier],
  }));

  // ── Pie: industry allocation (grouped by industry → sector fallback) ─────
  const industryBuckets: Record<string, number> = {};
  for (const r of rows) {
    const key = fundMap[r.symbol]?.industry
             || fundMap[r.symbol]?.sector
             || "Unknown";
    industryBuckets[key] = (industryBuckets[key] ?? 0) + r.total_invested;
  }
  // Sort descending, collapse slivers < 3% of total into "Other"
  const sortedBuckets = Object.entries(industryBuckets).sort((a, b) => b[1] - a[1]);
  const industryData: { name: string; value: number; color: string }[] = [];
  let otherVal = 0;
  sortedBuckets.forEach(([name, val], i) => {
    if (totalInvested > 0 && val / totalInvested < 0.03 && i >= 8) {
      otherVal += val;
    } else {
      industryData.push({
        name,
        value: parseFloat(val.toFixed(2)),
        color: HOLDING_PALETTE[i % HOLDING_PALETTE.length],
      });
    }
  });
  if (otherVal > 0) {
    industryData.push({ name: "Other", value: parseFloat(otherVal.toFixed(2)), color: "#4b5563" });
  }

  // ── Grouped bar: Invested vs Current Value by tier ────────────────────────
  const tierBarData = tierStats.map(t => ({
    name:     t.label,
    Invested: parseFloat(t.invested.toFixed(2)),
    Current:  parseFloat(t.currentValue.toFixed(2)),
    color:    CAP_COLORS[t.tier],
  }));

  // ── Horizontal bar: P&L % by holding ─────────────────────────────────────
  const pnlBarData = rows
    .filter(r => r.unrealized_pnl_pct != null)
    .slice()
    .sort((a, b) => (b.unrealized_pnl_pct ?? 0) - (a.unrealized_pnl_pct ?? 0))
    .map(r => ({
      name:  r.symbol,
      pnl:   parseFloat((r.unrealized_pnl_pct ?? 0).toFixed(2)),
      fill:  (r.unrealized_pnl_pct ?? 0) >= 0 ? "#10b981" : "#ef4444",
    }));

  // #11 — use outer inr(); remove duplicate inner one
  // Uses the module-level inr() defined below — but since that one returns JSX for null,
  // we need a local number-only formatter (non-null path only is called here)
  const fmtInr = (n: number) =>
    `₹${Math.abs(n).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

  const TOOLTIP_CONTENT = { background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 11 };
  const TOOLTIP_LABEL   = { color: "#9ca3af" };
  const TOOLTIP_ITEM    = { color: "#e5e7eb" };
  const CURSOR_STYLE    = { fill: "rgba(255,255,255,0.04)" };

  return (
    <div className="mb-6">
      {/* #7 — collapsible header */}
      <div
        className="flex items-center justify-between mb-4 cursor-pointer select-none group"
        onClick={() => setOpen(v => !v)}
      >
        <h2 className="text-sm font-semibold text-white group-hover:text-blue-300 transition-colors">Portfolio Analytics</h2>
        <ChevronDown
          size={15}
          className={`text-gray-500 transition-transform ${open ? "" : "-rotate-90"}`}
        />
      </div>
      {!open && null}
      {open && <>

      {/* Tab bar */}
      <div className="flex items-center gap-0 mb-4 border-b border-gray-800">
        {ANALYTICS_TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 text-xs font-medium transition-colors border-b-2 whitespace-nowrap ${
              activeTab === t.key
                ? "border-blue-500 text-white"
                : "border-transparent text-gray-500 hover:text-white"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab panels */}
      {activeTab === "cap_alloc" && (
        <div className="card py-4 px-5 mb-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Cap-Tier Allocation <span className="text-gray-600 font-normal normal-case">(by invested ₹)</span>
          </p>
          <ResponsiveContainer width="100%" height={260}>
            <RPieChart>
              <Pie
                data={allocationData}
                cx="50%" cy="50%"
                innerRadius={70} outerRadius={110}
                paddingAngle={3}
                dataKey="value"
              >
                {allocationData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <RTooltip
                contentStyle={TOOLTIP_CONTENT}
                labelStyle={TOOLTIP_LABEL}
                itemStyle={TOOLTIP_ITEM}
                formatter={(v: number) => [`₹${v.toLocaleString("en-IN")}`, "Invested"]}
              />
              <Legend
                iconType="circle" iconSize={8}
                wrapperStyle={{ fontSize: 12, color: "#9ca3af" }}
              />
            </RPieChart>
          </ResponsiveContainer>
        </div>
      )}

      {activeTab === "industry_alloc" && (
        <div className="card py-4 px-5 mb-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Industry Allocation <span className="text-gray-600 font-normal normal-case">(by invested ₹)</span>
          </p>
          <ResponsiveContainer width="100%" height={280}>
            <RPieChart>
              <Pie
                data={industryData}
                cx="50%" cy="50%"
                innerRadius={70} outerRadius={110}
                paddingAngle={2}
                dataKey="value"
              >
                {industryData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <RTooltip
                contentStyle={TOOLTIP_CONTENT}
                labelStyle={TOOLTIP_LABEL}
                itemStyle={TOOLTIP_ITEM}
                formatter={(v: number, name: string) => [
                  `₹${v.toLocaleString("en-IN")} (${totalInvested > 0 ? ((v / totalInvested) * 100).toFixed(1) : 0}%)`,
                  name,
                ]}
              />
              <Legend
                iconType="circle" iconSize={8}
                wrapperStyle={{ fontSize: 11, color: "#9ca3af" }}
                formatter={(value: string) => value.length > 26 ? value.slice(0, 25) + "…" : value}
              />
            </RPieChart>
          </ResponsiveContainer>
        </div>
      )}

      {activeTab === "tier_vs_current" && tierBarData.length > 0 && (
        <div className="card py-4 px-5 mb-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Invested vs Current Value <span className="text-gray-600 font-normal normal-case">(₹ by cap tier)</span>
          </p>
          <ResponsiveContainer width="100%" height={240}>
            <RBarChart data={tierBarData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis
                tick={{ fill: "#6b7280", fontSize: 11 }} tickLine={false} axisLine={false}
                tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`}
                width={52}
              />
              <RTooltip
                contentStyle={TOOLTIP_CONTENT}
                labelStyle={TOOLTIP_LABEL}
                itemStyle={TOOLTIP_ITEM}
                cursor={CURSOR_STYLE}
                formatter={(v: number, name: string) => [`₹${v.toLocaleString("en-IN")}`, name]}
              />
              <Legend iconType="square" iconSize={8} wrapperStyle={{ fontSize: 12, color: "#9ca3af" }} />
              <Bar dataKey="Invested" fill="#3b82f6" radius={[3, 3, 0, 0]} barSize={28} />
              <Bar dataKey="Current"  fill="#10b981" radius={[3, 3, 0, 0]} barSize={28} />
            </RBarChart>
          </ResponsiveContainer>
        </div>
      )}

      {activeTab === "pnl_pct" && pnlBarData.length > 0 && (
        <div className="card py-4 px-5 mb-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Unrealized P&amp;L % <span className="text-gray-600 font-normal normal-case">(per holding)</span>
          </p>
          <ResponsiveContainer width="100%" height={Math.max(200, pnlBarData.length * 36)}>
            <RBarChart data={pnlBarData} layout="vertical" margin={{ top: 4, right: 48, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" horizontal={false} />
              <XAxis
                type="number" tick={{ fill: "#6b7280", fontSize: 11 }} tickLine={false} axisLine={false}
                tickFormatter={v => `${v}%`}
              />
              <YAxis
                type="category" dataKey="name"
                tick={{ fill: "#9ca3af", fontSize: 12 }} tickLine={false} axisLine={false}
                width={72}
              />
              <RTooltip
                contentStyle={TOOLTIP_CONTENT}
                labelStyle={TOOLTIP_LABEL}
                itemStyle={TOOLTIP_ITEM}
                cursor={CURSOR_STYLE}
                formatter={(v: number) => [`${v >= 0 ? "+" : ""}${v.toFixed(2)}%`, "P&L"]}
              />
              <Bar dataKey="pnl" radius={[0, 3, 3, 0]} barSize={20}>
                {pnlBarData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
                <LabelList
                  dataKey="pnl"
                  position="right"
                  style={{ fill: "#9ca3af", fontSize: 11 }}
                  formatter={(v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`}
                />
              </Bar>
            </RBarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Cap-tier breakdown table */}
      {tierStats.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-800">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
              Breakdown by Cap Tier
            </p>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-800/40">
                <th className="th text-left">Tier</th>
                <th className="th text-right">Holdings</th>
                <th className="th text-right">Invested</th>
                <th className="th text-right">Current Value</th>
                <th className="th text-right">P&amp;L</th>
                <th className="th text-right">P&amp;L %</th>
                <th className="th text-right">Weight</th>
              </tr>
            </thead>
            <tbody>
              {tierStats.map(t => {
                const up = t.pnl >= 0;
                return (
                  <tr key={t.tier} className="border-t border-gray-800/60 hover:bg-gray-800/20 transition-colors">
                    <td className="td">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full inline-block shrink-0"
                          style={{ background: CAP_COLORS[t.tier] }}
                        />
                        <span className="font-medium text-gray-200">{t.label}</span>
                      </div>
                    </td>
                    <td className="td text-right text-gray-400">{t.count}</td>
                    <td className="td text-right font-mono text-gray-300">{fmtInr(t.invested)}</td>
                    <td className="td text-right font-mono text-white">{fmtInr(t.currentValue)}</td>
                    <td className={`td text-right font-mono ${up ? "gain" : "loss"}`}>
                      {up ? "+" : "−"}{fmtInr(t.pnl)}
                    </td>
                    <td className={`td text-right font-mono ${up ? "gain" : "loss"}`}>
                      {up ? "+" : ""}{t.pnlPct.toFixed(2)}%
                    </td>
                    <td className="td text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 bg-gray-800 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width:      `${Math.min((t.invested / totalInvested) * 100, 100).toFixed(1)}%`,
                              background: CAP_COLORS[t.tier],
                            }}
                          />
                        </div>
                        <span className="text-gray-400 w-9 text-right">
                          {((t.invested / totalInvested) * 100).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {/* Total row */}
              <tr className="border-t-2 border-gray-700 bg-gray-800/30">
                <td className="td font-semibold text-white">Total</td>
                <td className="td text-right text-gray-400">{rows.length}</td>
                <td className="td text-right font-mono font-semibold text-white">{fmtInr(totalInvested)}</td>
                <td className="td text-right font-mono font-semibold text-white">{fmtInr(totalValue)}</td>
                <td className={`td text-right font-mono font-semibold ${totalValue - totalInvested >= 0 ? "gain" : "loss"}`}>
                  {totalValue - totalInvested >= 0 ? "+" : "−"}{fmtInr(totalValue - totalInvested)}
                </td>
                <td className={`td text-right font-mono font-semibold ${totalValue - totalInvested >= 0 ? "gain" : "loss"}`}>
                  {totalInvested > 0
                    ? `${((totalValue - totalInvested) / totalInvested * 100) >= 0 ? "+" : ""}${((totalValue - totalInvested) / totalInvested * 100).toFixed(2)}%`
                    : "—"}
                </td>
                <td className="td text-right text-gray-500">100%</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
      </>}
    </div>
  );
}

// ── Market-cap tier tab definitions ───────────────────────────────────────────

type CapTierFilter = "all" | "large" | "mid" | "small" | "unknown";

const CAP_TIER_TABS: { key: CapTierFilter; label: string; color: string }[] = [
  { key: "all",     label: "All",       color: "text-white" },
  { key: "large",   label: "Large Cap", color: "text-blue-400" },
  { key: "mid",     label: "Mid Cap",   color: "text-purple-400" },
  { key: "small",   label: "Small Cap", color: "text-orange-400" },
  { key: "unknown", label: "Unknown",   color: "text-gray-500" },
];

const CAP_BADGE: Record<string, string> = {
  large:   "bg-blue-900/30 text-blue-400 border-blue-800/40",
  mid:     "bg-purple-900/30 text-purple-400 border-purple-800/40",
  small:   "bg-orange-900/30 text-orange-400 border-orange-800/40",
};

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
          : <ChevronsUpDown size={12} className="text-gray-500" />}
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
              {/* #5 — NSE|BSE toggle chip */}
              <div className="flex rounded-lg border border-gray-700 overflow-hidden w-full">
                {(["NSE", "BSE"] as const).map(ex => (
                  <button
                    key={ex} type="button"
                    onClick={() => setSelExchange(ex)}
                    className={`flex-1 py-2 text-sm font-semibold transition-colors ${
                      selExchange === ex
                        ? "bg-blue-600 text-white"
                        : "bg-gray-800 text-gray-400 hover:text-white"
                    }`}
                  >
                    {ex}
                  </button>
                ))}
              </div>
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
  // #4 — inline delete confirm; #10 — optimistic delete (row already gone before API)
  const [confirming, setConfirming] = useState(false);

  function handleDeleteClick(e: React.MouseEvent) {
    e.stopPropagation();
    setConfirming(true);
  }
  function handleConfirm(e: React.MouseEvent) {
    e.stopPropagation();
    onDelete(trade.id);   // caller does optimistic remove first (see #10 in PortfolioPage)
  }
  function handleCancel(e: React.MouseEvent) {
    e.stopPropagation();
    setConfirming(false);
  }

  return (
    <tr className={`transition-colors group ${confirming ? "bg-red-900/20" : "hover:bg-gray-800/30"}`}>
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
      <td className="td text-center w-28">
        {confirming ? (
          <span className="inline-flex items-center gap-1 text-xs">
            <span className="text-red-400 font-medium">Delete?</span>
            <button onClick={handleConfirm} className="text-red-400 hover:text-red-300 font-semibold px-1">Yes</button>
            <button onClick={handleCancel} className="text-gray-500 hover:text-white px-1">✕</button>
          </span>
        ) : (
          <button
            onClick={handleDeleteClick}
            className="text-gray-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
          >
            <Trash2 size={13} />
          </button>
        )}
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
  // #8 — collapsed by default; auto-expands when results arrive
  const [expanded, setExpanded] = useState(false);

  async function runAnalysis() {
    setLoading(true); setError(null);
    try {
      const data = await apiFetch<PortfolioAnalysis>("/trades/portfolio/analyse", { method: "POST" });
      setResult(data);
      if (data.status === "ok") setExpanded(true);   // #8 auto-expand on success
      else setError(data.summary ?? "Analysis failed");
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
  const [corpActions, setCorpActions] = useState<CorporateActionOut[]>([]);
  // Map of symbol → {industry, sector} from fundamentals cache
  const [fundMap, setFundMap]     = useState<Record<string, { industry: string | null; sector: string | null }>>({});
  // Auto-open modal when navigated from StockDetail with ?addTrade=SYMBOL
  const [showModal, setShowModal] = useState(!!prefillSymbol);
  const [showTrades, setShowTrades] = useState(false);

  function loadPortfolio() {
    apiFetch<PortfolioRow[]>("/trades/portfolio").then(rows => {
      setRows(rows);
      // Fetch fundamentals for all holdings (background) — populates industry map
      // and also seeds the backend cache for cap_tier on next portfolio load.
      const needsFund = rows.filter(r => r.cap_tier == null);
      Promise.all(
        rows.map(r =>
          apiFetch<{ industry: string | null; sector: string | null; error: string | null }>(
            `/analysis/${r.symbol}/fundamentals?exchange=${r.exchange}`
          ).catch(() => null)
            .then(f => f ? { sym: r.symbol, industry: f.industry, sector: f.sector } : null)
        )
      ).then(results => {
        const map: Record<string, { industry: string | null; sector: string | null }> = {};
        for (const item of results) {
          if (item) map[item.sym] = { industry: item.industry, sector: item.sector };
        }
        setFundMap(map);
        // Re-fetch portfolio if any were unclassified — backend cap_tier now populated
        if (needsFund.length > 0) {
          apiFetch<PortfolioRow[]>("/trades/portfolio")
            .then(setRows)
            .catch(() => null);
        }
      });
    }).catch(console.error);
  }
  function loadTrades() {
    tradesApi.list().then(setTrades).catch(console.error);
  }

  useEffect(() => {
    loadPortfolio();
    loadTrades();
    // Bug 5: load corporate actions so we can warn if any BONUS/SPLIT exist
    // that users should be aware of for avg-price accuracy
    corporateActionsApi.list().then(setCorpActions).catch(() => null);
  }, []);

  async function handleDeleteTrade(id: number) {
    // #10 — optimistic delete: remove from state immediately, then confirm with API
    setTrades(prev => prev.filter(t => t.id !== id));
    try {
      await tradesApi.remove(id);
      loadTrades();
      loadPortfolio();
    } catch {
      // Restore on failure by reloading
      loadTrades();
    }
  }

  const totalInvested   = rows.reduce((s, r) => s + r.total_invested, 0);
  const totalValue      = rows.reduce((s, r) => s + (r.current_value ?? r.total_invested), 0);
  const totalPnl        = totalValue - totalInvested;
  const totalPct        = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0;
  const gainers         = rows.filter(r => (r.unrealized_pnl ?? 0) > 0).length;
  const losers          = rows.filter(r => (r.unrealized_pnl ?? 0) < 0).length;
  // Realized P&L — sum all SELL trades that have a realized_pnl set
  const totalRealizedPnl = trades
    .filter(t => t.trade_type === "SELL" && t.realized_pnl != null)
    .reduce((s, t) => s + (t.realized_pnl ?? 0), 0);
  const hasRealized = trades.some(t => t.trade_type === "SELL" && t.realized_pnl != null);

  // #1 — P&L card tint class
  const pnlCardBg = totalPnl > 0
    ? "bg-emerald-900/20 border-emerald-800/40"
    : totalPnl < 0
    ? "bg-red-900/20 border-red-800/40"
    : "";
  const realizedCardBg = !hasRealized ? "" : totalRealizedPnl > 0
    ? "bg-emerald-900/20 border-emerald-800/40"
    : totalRealizedPnl < 0
    ? "bg-red-900/20 border-red-800/40"
    : "";

  const summaryCards = [
    { label: "Invested",         value: `₹${totalInvested.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,                                      sub: `${rows.length} holdings`,                            color: "text-white",                                tint: "" },
    { label: "Current Value",    value: `₹${totalValue.toLocaleString("en-IN",    { minimumFractionDigits: 2 })}`,                                      sub: "Mark to market",                                     color: "text-white",                                tint: "" },
    { label: "Unrealized P&L",   value: `${totalPnl >= 0 ? "+" : ""}₹${Math.abs(totalPnl).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,     sub: `${totalPct >= 0 ? "+" : ""}${totalPct.toFixed(2)}%`, color: totalPnl >= 0 ? "gain" : "loss",             tint: pnlCardBg },
    { label: "Realized P&L",     value: hasRealized
        ? `${totalRealizedPnl >= 0 ? "+" : ""}₹${Math.abs(totalRealizedPnl).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
        : "—",                                                                                                                                           sub: hasRealized ? "from closed positions" : "No sells yet", color: hasRealized ? (totalRealizedPnl >= 0 ? "gain" : "loss") : "text-gray-600", tint: realizedCardBg },
    { label: "Gainers / Losers", value: `${gainers} / ${losers}`,                                                                                       sub: `${rows.length - gainers - losers} neutral`,           color: "text-white",                                tint: "" },
  ];

  // ── Cap-tier tab ──────────────────────────────────────────────────────────
  const [capTier, setCapTier] = useState<CapTierFilter>("all");

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
    numericKeys: ["qty", "avg_price", "invested", "ltp", "current_value", "pnl", "pnl_pct"],
  });

  // Apply cap-tier filter on top of text filter
  const tierFiltered = holdingsSort.filtered.filter(r => {
    if (capTier === "all")     return true;
    if (capTier === "unknown") return r.cap_tier == null;
    return r.cap_tier === capTier;
  });

  const displayedHoldings = holdingsFilter.trim()
    ? tierFiltered.filter(r =>
        `${r.symbol} ${r.company_name ?? ""}`.toLowerCase().includes(holdingsFilter.trim().toLowerCase())
      )
    : tierFiltered;

  // ── Cap-tier summary counts ───────────────────────────────────────────────
  const capCounts: Record<CapTierFilter, number> = {
    all:     rows.length,
    large:   rows.filter(r => r.cap_tier === "large").length,
    mid:     rows.filter(r => r.cap_tier === "mid").length,
    small:   rows.filter(r => r.cap_tier === "small").length,
    unknown: rows.filter(r => r.cap_tier == null).length,
  };

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
    numericKeys: ["qty", "price", "brokerage", "realized_pnl"],
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

      {/* Summary cards — #1: P&L card gets green/red tint; 5 cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-4">
        {summaryCards.map(c => (
          <div key={c.label} className={`card border ${c.tint || "border-gray-800"}`}>
            <p className="text-xs text-gray-500 uppercase tracking-wide">{c.label}</p>
            <p className={`text-xl font-bold mt-2 ${c.color}`}>{c.value}</p>
            <p className="text-xs text-gray-500 mt-1">{c.sub}</p>
          </div>
        ))}
      </div>

      {/* #2 — Cost basis fuel gauge bar */}
      {rows.length > 0 && totalInvested > 0 && (
        <div className="mb-6 px-1">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-1.5">
            <span>Cost Basis</span>
            <span>
              ₹{totalInvested.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
              {" → "}
              <span className={totalPnl >= 0 ? "text-emerald-400" : "text-red-400"}>
                ₹{totalValue.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
              </span>
            </span>
          </div>
          <div className="relative h-2 rounded-full overflow-hidden bg-gray-800">
            {/* invested baseline */}
            <div className="absolute inset-0 rounded-full bg-gray-700" />
            {/* current value fill — capped at 200% to avoid runaway visuals */}
            <div
              className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${totalPnl >= 0 ? "bg-emerald-500" : "bg-red-500"}`}
              style={{ width: `${Math.min((totalValue / totalInvested) * 100, 200).toFixed(1)}%` }}
            />
            {/* 100% tick mark */}
            <div className="absolute top-0 bottom-0 w-px bg-gray-500/70" style={{ left: "50%" }} />
          </div>
          <div className="flex justify-between text-xs text-gray-600 mt-1">
            <span>0%</span>
            <span className="text-gray-500">Cost basis (100%)</span>
            <span>200%</span>
          </div>
        </div>
      )}

      {/* Bug 5: Corporate action warning — show if any BONUS or SPLIT is recorded */}
      {corpActions.filter(a => a.action_type === "BONUS" || a.action_type === "SPLIT").length > 0 && (
        <div className="mb-4 flex items-start gap-3 bg-yellow-900/20 border border-yellow-700/40 rounded-xl px-5 py-3.5">
          <AlertTriangle size={16} className="text-yellow-400 shrink-0 mt-0.5" />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-yellow-300">Corporate Actions on record</p>
            <p className="text-xs text-yellow-200/70 mt-0.5">
              {corpActions.filter(a => a.action_type === "BONUS" || a.action_type === "SPLIT")
                .map(a => `${a.symbol} ${a.action_type}${a.ratio ? ` (${a.ratio})` : ""} on ${a.action_date}`)
                .join(" · ")
              }
            </p>
            <p className="text-xs text-yellow-200/50 mt-1">
              These actions have been applied to your portfolio quantities and avg prices.
              If you recorded this action via the API but have not yet verified your avg price, please review your holdings.
            </p>
          </div>
        </div>
      )}

      {/* AI Portfolio Review */}
      <PortfolioReviewCard hasHoldings={rows.length > 0} />

      {/* Portfolio Analytics */}
      {rows.length > 0 && <PortfolioAnalyticsPanel rows={rows} fundMap={fundMap} />}

      {/* Cap-tier tab bar — #12: shimmer while fundMap empty */}
      {rows.length > 0 && (
        <div className="flex items-center gap-0 mb-4 border-b border-gray-800">
          {CAP_TIER_TABS.filter(t => t.key === "all" || capCounts[t.key] > 0).map(t => {
            const isLoading = t.key !== "all" && Object.keys(fundMap).length === 0 && rows.length > 0;
            return (
              <button
                key={t.key}
                onClick={() => setCapTier(t.key)}
                className={`px-4 py-2.5 text-xs font-medium transition-colors border-b-2 ${
                  capTier === t.key
                    ? `border-blue-500 ${t.color}`
                    : "border-transparent text-gray-500 hover:text-white"
                }`}
              >
                {isLoading ? (
                  <span className="inline-block h-2.5 w-14 bg-gray-700 animate-pulse rounded" />
                ) : (
                  <>
                    {t.label}
                    {capCounts[t.key] > 0 && (
                      <span className="ml-1.5 text-gray-600 font-normal">({capCounts[t.key]})</span>
                    )}
                  </>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Holdings text filter */}
      {rows.length > 0 && (
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
              // #3 — colour-coded left border by P&L magnitude
              const absPct = Math.abs(pct ?? 0);
              const borderColor =
                pnl == null  ? "border-gray-800" :
                !up          ? (absPct >= 10 ? "border-red-500" : absPct >= 3 ? "border-red-400" : "border-red-900") :
                               (absPct >= 10 ? "border-emerald-500" : absPct >= 3 ? "border-emerald-400" : "border-emerald-900");
              return (
                <tr
                  key={r.id}
                  onClick={() => navigate(`/stock/${r.symbol}?exchange=${r.exchange}`)}
                  className="hover:bg-gray-800/40 cursor-pointer transition-colors"
                >
                  <td className={`td border-l-2 ${borderColor}`}>
                    <div className="flex flex-col">
                      <span className="font-semibold text-white">{r.company_name || r.symbol}</span>
                      <span className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                        <span className="font-mono text-xs text-gray-500">{r.symbol}</span>
                        <span className="text-xs bg-gray-800 text-gray-500 px-1.5 py-px rounded">{r.exchange}</span>
                        {r.cap_tier && (
                          <span className={`text-xs px-1.5 py-px rounded border ${CAP_BADGE[r.cap_tier]}`}>
                            {r.cap_tier === "large" ? "L" : r.cap_tier === "mid" ? "M" : "S"} Cap
                          </span>
                        )}
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

            <div className="flex items-center gap-2">
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
              {/* Export CSV */}
              <a
                href={`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/trades/export`}
                download="trades_all.csv"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-700 text-xs text-gray-400 hover:text-white hover:border-gray-600 transition-colors"
                title="Export all transactions as CSV"
              >
                <Download size={12} />
                Export CSV
              </a>
            </div>
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
