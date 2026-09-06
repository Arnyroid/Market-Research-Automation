import { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  BarChart2, ChevronRight, ChevronDown, RefreshCw, ExternalLink,
  TrendingUp, TrendingDown, Minus, Search, Sparkles, AlertTriangle,
} from "lucide-react";
import { marketApi, SectorInfo, IndustryNode, IndustryStock, IndustryPageResult, IndustryOverviewRow, SectorAnalysis, SectorSignal, IndustrySignal } from "../api/market";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtCr(n: number | null | undefined) {
  if (n == null) return <span className="text-gray-600">—</span>;
  if (Math.abs(n) >= 100_000) return `₹${(n / 100_000).toFixed(1)}L Cr`;
  if (Math.abs(n) >= 1_000)   return `₹${(n / 1_000).toFixed(1)}k Cr`;
  return `₹${n.toFixed(0)} Cr`;
}

function VarCell({ v }: { v: number | null }) {
  if (v == null) return <span className="text-gray-600">—</span>;
  const cls  = v > 0 ? "gain" : v < 0 ? "loss" : "text-gray-400";
  const Icon = v > 0 ? TrendingUp : v < 0 ? TrendingDown : Minus;
  return (
    <span className={`${cls} inline-flex items-center gap-0.5`}>
      <Icon size={10} />
      {v > 0 ? "+" : ""}{v.toFixed(1)}%
    </span>
  );
}

// ── Palette ───────────────────────────────────────────────────────────────────

const SECTOR_COLORS = [
  "#3b82f6","#8b5cf6","#06b6d4","#10b981",
  "#f59e0b","#f97316","#ef4444","#a78bfa",
  "#34d399","#fbbf24","#60a5fa","#c084fc",
];

// ── Tree node component ───────────────────────────────────────────────────────

function TreeNode({
  node,
  activePath,
  onSelect,
  indent = 0,
}: {
  node: IndustryNode;
  activePath: string | null;
  onSelect: (n: IndustryNode) => void;
  indent?: number;
}) {
  const isLeaf   = node.children.length === 0;
  const isActive = activePath === node.path;
  const [open, setOpen] = useState(false);

  // Auto-expand when a descendant becomes active
  useEffect(() => {
    if (!isLeaf) {
      const anyChildActive = node.children.some(
        c => activePath === c.path || (activePath && activePath.startsWith(c.path))
      );
      if (anyChildActive) setOpen(true);
    }
  }, [activePath, isLeaf]);

  const countLabel = node.total_stocks > 0
    ? <span className="text-[10px] text-gray-600 shrink-0 ml-1">{node.total_stocks}</span>
    : null;

  if (isLeaf) {
    return (
      <div
        role="button"
        onClick={() => onSelect(node)}
        className={`flex items-center gap-1.5 py-1 rounded-lg text-xs cursor-pointer transition-colors ${
          isActive ? "bg-blue-600/20 text-blue-300" : "text-gray-400 hover:bg-gray-800/60 hover:text-white"
        }`}
        style={{ paddingLeft: `${8 + indent * 14}px`, paddingRight: "8px" }}
      >
        <span className="w-2.5 h-2.5 rounded-full shrink-0 border border-gray-700 inline-block" />
        <span className="flex-1 leading-snug">{node.name}</span>
        {countLabel}
      </div>
    );
  }

  return (
    <div>
      <div
        className={`flex items-center rounded-lg text-xs transition-colors ${
          isActive ? "bg-blue-600/20 text-blue-300" : "text-gray-400 hover:bg-gray-800/60 hover:text-white"
        }`}
        style={{ paddingLeft: `${8 + indent * 14}px`, paddingRight: "4px" }}
      >
        {/* Chevron — toggles expand/collapse only */}
        <button
          onClick={() => setOpen(v => !v)}
          className="shrink-0 p-1 rounded hover:bg-gray-700/50 transition-colors"
          aria-label={open ? "Collapse" : "Expand"}
        >
          {open
            ? <ChevronDown  size={11} className="text-gray-500" />
            : <ChevronRight size={11} className="text-gray-500" />}
        </button>
        {/* Label — selects the node (loads stocks) */}
        <button
          onClick={() => onSelect(node)}
          className="flex-1 flex items-center gap-1 py-1 text-left"
        >
          <span className="flex-1 leading-snug">{node.name}</span>
          {countLabel}
        </button>
      </div>
      {open && (
        <div>
          {node.children.map(child => (
            <TreeNode
              key={child.path}
              node={child}
              activePath={activePath}
              onSelect={onSelect}
              indent={indent + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── AI Sector Pulse panel ─────────────────────────────────────────────────────

const SIG_STYLES: Record<string, { bg: string; text: string; dot: string }> = {
  BUY:   { bg: "bg-emerald-900/30", text: "text-emerald-400", dot: "bg-emerald-500" },
  HOLD:  { bg: "bg-yellow-900/20",  text: "text-yellow-400",  dot: "bg-yellow-500" },
  AVOID: { bg: "bg-red-900/25",     text: "text-red-400",     dot: "bg-red-500"     },
};

function SignalBadge({ signal }: { signal: "BUY" | "HOLD" | "AVOID" }) {
  const s = SIG_STYLES[signal] ?? SIG_STYLES.HOLD;
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold ${s.bg} ${s.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {signal}
    </span>
  );
}

function SectorPulsePanel({
  analysis,
  loading,
  error,
  onRefresh,
}: {
  analysis: SectorAnalysis | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}) {
  const [open, setOpen] = useState(true);
  const [tab,  setTab]  = useState<"sectors" | "buy" | "avoid">("sectors");

  return (
    <div className="card mb-5 overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center gap-2 px-4 py-3 cursor-pointer select-none border-b border-gray-800/60"
        onClick={() => setOpen(v => !v)}
      >
        <Sparkles size={14} className="text-purple-400 shrink-0" />
        <span className="text-sm font-semibold text-white flex-1">AI Sector Pulse</span>
        {analysis && (
          <span className="text-[10px] text-gray-500 shrink-0">
            {analysis.generated_at} · 24h cache
          </span>
        )}
        <button
          className="btn-ghost text-xs flex items-center gap-1 px-2 py-1 shrink-0"
          onClick={e => { e.stopPropagation(); onRefresh(); }}
          disabled={loading}
          title="Regenerate analysis"
        >
          <RefreshCw size={11} className={loading ? "animate-spin" : ""} />
        </button>
        <ChevronDown size={13} className={`text-gray-500 transition-transform shrink-0 ${open ? "" : "-rotate-90"}`} />
      </div>

      {open && (
        <div className="px-4 py-3">
          {/* Loading */}
          {loading && (
            <div className="flex items-center gap-2 text-gray-500 text-sm py-6 justify-center">
              <RefreshCw size={15} className="animate-spin" />
              Asking Gemini to analyse all 188 industries… (may take ~10s)
            </div>
          )}

          {/* Error */}
          {error && !loading && (
            <div className="flex items-center gap-2 text-yellow-400 text-xs bg-yellow-900/10 border border-yellow-800/30 rounded-lg px-3 py-2">
              <AlertTriangle size={13} />
              {error}
            </div>
          )}

          {/* Analysis */}
          {analysis && !loading && (
            <div className="space-y-4">
              {/* Market summary */}
              <p className="text-xs text-gray-300 leading-relaxed border-l-2 border-purple-500/60 pl-3">
                {analysis.market_summary}
              </p>

              {/* Tabs */}
              <div className="flex gap-1 text-xs">
                {(["sectors", "buy", "avoid"] as const).map(t => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                      tab === t
                        ? t === "buy" ? "bg-emerald-900/40 text-emerald-300"
                          : t === "avoid" ? "bg-red-900/30 text-red-300"
                          : "bg-gray-700 text-white"
                        : "text-gray-500 hover:text-gray-300"
                    }`}
                  >
                    {t === "sectors" ? "Sectors" : t === "buy" ? "Top 5 Buy" : "Top 5 Avoid"}
                  </button>
                ))}
              </div>

              {/* Sectors grid */}
              {tab === "sectors" && (
                <div className="grid grid-cols-2 gap-2">
                  {analysis.sectors.map((sec, i) => {
                    const s = SIG_STYLES[sec.signal] ?? SIG_STYLES.HOLD;
                    return (
                      <div key={i} className={`rounded-lg px-3 py-2 border border-gray-800/60 ${s.bg}`}>
                        <div className="flex items-center gap-2 mb-1">
                          <SignalBadge signal={sec.signal} />
                          <span className="text-xs font-medium text-white truncate">{sec.name}</span>
                        </div>
                        <p className="text-[11px] text-gray-400 leading-snug">{sec.rationale}</p>
                        <p className={`text-[10px] mt-1 font-mono ${s.text}`}>{sec.key_metrics}</p>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Top-5 industries */}
              {(tab === "buy" || tab === "avoid") && (
                <div className="space-y-2">
                  {(tab === "buy" ? analysis.top_buy_industries : analysis.top_avoid_industries).map((ind, i) => {
                    const signal = tab === "buy" ? "BUY" : "AVOID";
                    const s = SIG_STYLES[signal];
                    return (
                      <div key={i} className={`rounded-lg px-3 py-2 border border-gray-800/60 ${s.bg}`}>
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-[11px] font-bold tabular-nums text-gray-600 w-4 shrink-0">{i + 1}</span>
                          <span className="text-xs font-medium text-white flex-1">{ind.name}</span>
                          <span className={`text-[10px] font-mono ${s.text} shrink-0`}>{ind.metrics}</span>
                        </div>
                        <p className="text-[11px] text-gray-400 leading-snug pl-6">{ind.rationale}</p>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Disclaimer */}
              <p className="text-[10px] text-gray-600 border-t border-gray-800/40 pt-2">
                {analysis.disclaimer}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Overview table (all 188 industries, shown when no sector selected) ────────

type OvSortKey = keyof IndustryOverviewRow;

function OverviewTable({
  rows,
  onSelect,
}: {
  rows: IndustryOverviewRow[];
  onSelect: (path: string) => void;
}) {
  const [sortKey, setSortKey] = useState<OvSortKey>("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [filter, setFilter]   = useState("");

  function handleSort(key: OvSortKey) {
    if (key === sortKey) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  }

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return q ? rows.filter(r => r.name.toLowerCase().includes(q)) : rows;
  }, [rows, filter]);

  const sorted = useMemo(() => [...filtered].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = typeof av === "number" && typeof bv === "number"
      ? av - bv : String(av).localeCompare(String(bv));
    return sortDir === "asc" ? cmp : -cmp;
  }), [filtered, sortKey, sortDir]);

  function Th({ label, sk, cls = "" }: { label: string; sk: OvSortKey; cls?: string }) {
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
      </th>
    );
  }

  function PctCell({ v, thresholdGood = 15, thresholdBad = 0 }: { v: number | null; thresholdGood?: number; thresholdBad?: number }) {
    if (v == null) return <span className="text-gray-600">—</span>;
    const cls = v >= thresholdGood ? "text-emerald-400" : v < thresholdBad ? "text-red-400" : "text-gray-300";
    return <span className={`${cls} tabular-nums`}>{v > 0 ? "+" : ""}{v.toFixed(1)}%</span>;
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <div>
          <h3 className="text-sm font-semibold text-white">All Industries</h3>
          <p className="text-xs text-gray-500">Aggregate metrics from screener.in · {sorted.length} of {rows.length} shown</p>
        </div>
        <div className="flex-1" />
        <div className="relative shrink-0">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input text-xs py-1.5 pl-7 pr-3 w-48"
            placeholder="Filter industries…"
            value={filter}
            onChange={e => setFilter(e.target.value)}
          />
        </div>
      </div>
      <div className="overflow-x-auto rounded-xl border border-gray-800">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-800/50">
              <th className="th text-right w-8">#</th>
              <Th label="Industry"     sk="name"         cls="text-left" />
              <Th label="Cos."         sk="num_companies" cls="text-right" />
              <Th label="Total MCap"   sk="total_mktcap"  cls="text-right" />
              <Th label="Median MCap"  sk="median_mktcap" cls="text-right" />
              <Th label="Med P/E"      sk="median_pe"     cls="text-right" />
              <Th label="Sales Gr %"   sk="sales_growth"  cls="text-right" />
              <Th label="OPM %"        sk="avg_opm"       cls="text-right" />
              <Th label="ROCE %"       sk="avg_roce"      cls="text-right" />
              <Th label="1Y Ret %"     sk="return_1y"     cls="text-right" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => (
              <tr
                key={i}
                className="border-t border-gray-800/60 hover:bg-gray-800/30 cursor-pointer transition-colors"
                onClick={() => onSelect(r.path)}
              >
                <td className="td text-right text-gray-600 tabular-nums">{r.rank}</td>
                <td className="td">
                  <span className="text-white font-medium">{r.name}</span>
                </td>
                <td className="td text-right tabular-nums text-gray-300">
                  {r.num_companies ?? "—"}
                </td>
                <td className="td text-right tabular-nums text-gray-300">{fmtCr(r.total_mktcap)}</td>
                <td className="td text-right tabular-nums text-gray-300">{fmtCr(r.median_mktcap)}</td>
                <td className="td text-right tabular-nums text-gray-300">
                  {r.median_pe != null ? `${r.median_pe.toFixed(1)}x` : "—"}
                </td>
                <td className="td text-right"><PctCell v={r.sales_growth} thresholdGood={10} thresholdBad={0} /></td>
                <td className="td text-right"><PctCell v={r.avg_opm}     thresholdGood={15} thresholdBad={5} /></td>
                <td className="td text-right"><PctCell v={r.avg_roce}    thresholdGood={15} thresholdBad={8} /></td>
                <td className="td text-right"><PctCell v={r.return_1y}   thresholdGood={15} thresholdBad={0} /></td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={10} className="td text-center text-gray-500 py-8">
                  {filter ? "No industries match your filter." : "No data available."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Stock table ───────────────────────────────────────────────────────────────

type SortKey = keyof IndustryStock;

function StockTable({
  title, stocks, onNavigate,
}: {
  title: string;
  stocks: IndustryStock[];
  onNavigate: (sym: string) => void;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("market_cap");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [filter, setFilter]   = useState("");

  function handleSort(key: SortKey) {
    if (key === sortKey) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  }

  const filtered = useMemo(() => stocks.filter(s =>
    !filter.trim() ||
    s.name.toLowerCase().includes(filter.toLowerCase()) ||
    (s.symbol ?? "").toLowerCase().includes(filter.toLowerCase())
  ), [stocks, filter]);

  const sorted = useMemo(() => [...filtered].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    const cmp = typeof av === "number" && typeof bv === "number"
      ? av - bv : String(av).localeCompare(String(bv));
    return sortDir === "asc" ? cmp : -cmp;
  }), [filtered, sortKey, sortDir]);

  function Th({ label, sk, cls = "" }: { label: string; sk: SortKey; cls?: string }) {
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
      </th>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <h3 className="text-sm font-semibold text-white flex-1 truncate">{title}</h3>
        <span className="text-xs text-gray-500 shrink-0">{sorted.length} co.</span>
        <div className="relative shrink-0">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input text-xs py-1.5 pl-7 pr-3 w-44"
            placeholder="Filter…"
            value={filter}
            onChange={e => setFilter(e.target.value)}
          />
        </div>
      </div>
      <div className="overflow-x-auto rounded-xl border border-gray-800">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-800/50">
              <th className="th text-right w-8">#</th>
              <Th label="Company"     sk="name"           cls="text-left" />
              <Th label="CMP (₹)"     sk="cmp"            cls="text-right" />
              <Th label="P/E"         sk="pe_ratio"       cls="text-right" />
              <Th label="Mkt Cap"     sk="market_cap"     cls="text-right" />
              <Th label="ROCE %"      sk="roce"           cls="text-right" />
              <Th label="Div Yld %"   sk="div_yield"      cls="text-right" />
              <Th label="NP Qtr"      sk="net_profit_qtr" cls="text-right" />
              <Th label="NP Var %"    sk="qtr_profit_var" cls="text-right" />
              <Th label="Sales Qtr"   sk="sales_qtr"      cls="text-right" />
              <Th label="Sales Var %" sk="qtr_sales_var"  cls="text-right" />
              <th className="th w-8" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((s, i) => (
              <tr
                key={i}
                className={`border-t border-gray-800/60 transition-colors ${s.symbol ? "hover:bg-gray-800/30 cursor-pointer" : ""}`}
                onClick={() => s.symbol && onNavigate(s.symbol)}
              >
                <td className="td text-right text-gray-600 tabular-nums">{s.rank}</td>
                <td className="td">
                  <span className="text-white font-medium">{s.name}</span>
                  {s.symbol && <span className="ml-1.5 text-gray-500 font-mono text-[10px]">{s.symbol}</span>}
                </td>
                <td className="td text-right font-mono tabular-nums text-gray-200">
                  {s.cmp != null ? s.cmp.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : "—"}
                </td>
                <td className="td text-right tabular-nums text-gray-300">
                  {s.pe_ratio != null ? `${s.pe_ratio.toFixed(1)}x` : "—"}
                </td>
                <td className="td text-right tabular-nums text-gray-300">{fmtCr(s.market_cap)}</td>
                <td className={`td text-right tabular-nums ${
                  s.roce != null ? s.roce >= 15 ? "text-emerald-400" : s.roce < 10 ? "text-red-400" : "text-gray-300" : ""
                }`}>
                  {s.roce != null ? `${s.roce.toFixed(1)}%` : "—"}
                </td>
                <td className="td text-right tabular-nums text-gray-300">
                  {s.div_yield != null ? `${s.div_yield.toFixed(2)}%` : "—"}
                </td>
                <td className="td text-right tabular-nums text-gray-300">{fmtCr(s.net_profit_qtr)}</td>
                <td className="td text-right"><VarCell v={s.qtr_profit_var} /></td>
                <td className="td text-right tabular-nums text-gray-300">{fmtCr(s.sales_qtr)}</td>
                <td className="td text-right"><VarCell v={s.qtr_sales_var} /></td>
                <td
                  className="td text-center"
                  onClick={e => { e.stopPropagation(); if (s.symbol) window.open(`https://www.screener.in/company/${s.symbol}/`, "_blank"); }}
                >
                  {s.symbol && <ExternalLink size={12} className="text-gray-600 hover:text-gray-400 transition-colors" />}
                </td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={12} className="td text-center text-gray-500 py-8">
                  {filter ? "No companies match your filter." : "No data available."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Collapsible L1 sector row ─────────────────────────────────────────────────

function SectorRow({
  sector, color, activeSector, activePath, onSelectSector, onSelectNode,
}: {
  sector: SectorInfo;
  color: string;
  activeSector: string | null;
  activePath: string | null;
  onSelectSector: (code: string) => void;
  onSelectNode: (n: IndustryNode) => void;
}) {
  const isActive = activeSector === sector.code;
  // Sectors with an active sub-path start expanded; otherwise collapsed
  const [open, setOpen] = useState(isActive);

  // Auto-expand when this sector becomes active via URL navigation
  useEffect(() => {
    if (isActive) setOpen(true);
  }, [isActive]);

  return (
    <div>
      {/* L1 row: chevron (collapse only) + coloured dot + label (select) */}
      <div
        className={`flex items-center rounded-lg text-xs font-medium transition-colors ${
          isActive ? "text-white bg-gray-800" : "text-gray-400 hover:bg-gray-800/60 hover:text-white"
        }`}
      >
        {/* Chevron — toggles collapse independently */}
        <button
          onClick={() => setOpen(v => !v)}
          className="shrink-0 p-1.5 rounded hover:bg-gray-700/50 transition-colors"
          aria-label={open ? "Collapse" : "Expand"}
        >
          <ChevronDown
            size={11}
            className={`text-gray-500 transition-transform ${open ? "" : "-rotate-90"}`}
          />
        </button>
        {/* Label — loads sector stocks */}
        <button
          onClick={() => onSelectSector(sector.code)}
          className="flex-1 flex items-center gap-2 py-1.5 pr-2 text-left"
        >
          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: color }} />
          <span className="flex-1 leading-snug">{sector.name}</span>
          {sector.total_stocks > 0 && (
            <span className="text-gray-600 text-[10px] shrink-0">{sector.total_stocks.toLocaleString()}</span>
          )}
        </button>
      </div>

      {/* L2 → L4 tree */}
      {open && sector.children.length > 0 && (
        <div className="ml-1 mt-0.5 mb-1">
          {sector.children.map(node => (
            <TreeNode
              key={node.path}
              node={node}
              activePath={activePath ? `/market/${activePath}/` : null}
              onSelect={onSelectNode}
              indent={0}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function IndustryPage() {
  const navigate = useNavigate();
  const [sp, setSp] = useSearchParams();

  const [sectors, setSectors]             = useState<SectorInfo[]>([]);
  const [sectorsLoading, setSectorsLoading] = useState(true);
  const [sectorsError, setSectorsError]   = useState<string | null>(null);
  const [industrySearch, setIndustrySearch] = useState("");

  const [overview, setOverview]             = useState<IndustryOverviewRow[]>([]);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError]   = useState<string | null>(null);

  const [pulse, setPulse]             = useState<SectorAnalysis | null>(null);
  const [pulseLoading, setPulseLoading] = useState(true);
  const [pulseError, setPulseError]   = useState<string | null>(null);

  // active* are URL-driven
  const activeSector = sp.get("sector") ?? null;   // L1 code e.g. "IN08"
  const activePath   = sp.get("path")   ?? null;   // full path e.g. "IN08/IN0801/IN080101/IN080101001"

  const [page, setPage]           = useState<IndustryPageResult | null>(null);
  const [pageLoading, setPageLoading] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);

  // Load sector tree, overview and AI pulse on mount (three independent requests)
  useEffect(() => {
    setSectorsLoading(true);
    setSectorsError(null);
    marketApi.getSectors()
      .then(setSectors)
      .catch(e => setSectorsError(e.message ?? "Failed to load sector index"))
      .finally(() => setSectorsLoading(false));

    setOverviewLoading(true);
    setOverviewError(null);
    marketApi.getOverview()
      .then(setOverview)
      .catch(e => setOverviewError(e.message ?? "Failed to load industry overview"))
      .finally(() => setOverviewLoading(false));

    setPulseLoading(true);
    setPulseError(null);
    marketApi.getSectorAnalysis()
      .then(setPulse)
      .catch(e => setPulseError(e.message ?? "AI sector analysis unavailable"))
      .finally(() => setPulseLoading(false));
  }, []);

  // Load stock table whenever active path or sector changes
  const loadPage = useCallback((rawPath: string, force = false) => {
    setPageLoading(true);
    setPageError(null);
    setPage(null);
    marketApi.getSectorStocks(rawPath, force)
      .then(setPage)
      .catch(e => setPageError(e.message ?? "Failed to load stocks"))
      .finally(() => setPageLoading(false));
  }, []);

  useEffect(() => {
    const path = activePath ?? activeSector;
    if (path) loadPage(path);
    else { setPage(null); setPageError(null); }
  }, [activeSector, activePath, loadPage]);

  // ── Helper: navigate to a node ────────────────────────────────────────────
  function selectNode(node: IndustryNode) {
    const clean = node.path.replace(/^\/market\//, "").replace(/\/$/, "");
    const code  = clean.split("/")[0];
    if (clean === code) setSp({ sector: code });
    else setSp({ sector: code, path: clean });
  }

  function selectSector(code: string) {
    setSp({ sector: code });
  }

  // Handle click from overview table: path is /market/L1/.../L4/ → derive sector + full path
  function selectOverviewRow(path: string) {
    const clean = path.replace(/^\/market\//, "").replace(/\/$/, "");
    const parts = clean.split("/");
    if (parts.length === 1) setSp({ sector: parts[0] });
    else setSp({ sector: parts[0], path: clean });
  }

  // ── Flat industry list (all 188) filtered by search ───────────────────────
  const allIndustries = useMemo(
    () => sectors.flatMap(s => s.flat_industries),
    [sectors]
  );
  const filteredIndustries = useMemo(() => {
    const q = industrySearch.trim().toLowerCase();
    if (!q) return allIndustries;
    return allIndustries.filter(n => n.name.toLowerCase().includes(q));
  }, [allIndustries, industrySearch]);

  const activeSectorInfo = sectors.find(s => s.code === activeSector) ?? null;

  // Resolve the active node title for breadcrumb
  const activeNodeName = useMemo(() => {
    if (!activePath || !activeSectorInfo) return null;
    const searchPath = `/market/${activePath}/`;
    function find(nodes: IndustryNode[]): string | null {
      for (const n of nodes) {
        if (n.path === searchPath) return n.name;
        const r = find(n.children);
        if (r) return r;
      }
      return null;
    }
    return find(activeSectorInfo.children);
  }, [activePath, activeSectorInfo]);

  return (
    <div className="max-w-screen-xl mx-auto">

      {/* Sticky header bar */}
      <div className="sticky top-0 z-20 bg-gray-950 border-b border-gray-800/60 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <BarChart2 size={20} className="text-blue-400" />
              <h1 className="text-2xl font-bold text-white">Industry Dashboard</h1>
            </div>
            <p className="text-gray-400 text-sm mt-0.5">
              {sectorsLoading
                ? "Loading sectors…"
                : `${sectors.length} sectors · ${allIndustries.length} industries · screener.in · 4h cache`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Refresh overview when no sector selected */}
            {!activeSector && overview.length > 0 && (
              <button
                className="btn-ghost text-xs flex items-center gap-1.5"
                onClick={() => {
                  setOverviewLoading(true);
                  marketApi.getOverview(true)
                    .then(setOverview)
                    .catch(e => setOverviewError(e.message))
                    .finally(() => setOverviewLoading(false));
                }}
                disabled={overviewLoading}
              >
                <RefreshCw size={12} className={overviewLoading ? "animate-spin" : ""} />
                Refresh
              </button>
            )}
            {/* Refresh stock table when viewing a sector/industry */}
            {(activePath || activeSector) && page && (
              <button
                className="btn-ghost text-xs flex items-center gap-1.5"
                onClick={() => loadPage(activePath ?? activeSector!, true)}
                disabled={pageLoading}
              >
                <RefreshCw size={12} className={pageLoading ? "animate-spin" : ""} />
                Refresh
              </button>
            )}
            <a href="https://www.screener.in/market/" target="_blank" rel="noopener noreferrer"
              className="btn-ghost text-xs flex items-center gap-1.5">
              <ExternalLink size={12} /> screener.in
            </a>
          </div>
        </div>
      </div>

      <div className="flex gap-5 items-start px-6 pt-5">

        {/* ── Left sidebar — sticky below the header, search pinned, tree scrolls ── */}
        <div className="w-64 shrink-0 sticky top-[73px] max-h-[calc(100vh-73px)] flex flex-col gap-2">

          {/* Search + quick-results — pinned, never scrolls */}
          <div className="shrink-0 flex flex-col gap-2">
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                className="input text-xs py-2 pl-8 pr-3 w-full"
                placeholder="Search all 188 industries…"
                value={industrySearch}
                onChange={e => setIndustrySearch(e.target.value)}
              />
            </div>

            {industrySearch.trim() && (
              <div className="card p-2 max-h-64 overflow-y-auto">
                {filteredIndustries.length === 0 ? (
                  <p className="text-xs text-gray-500 px-2 py-1">No industries match.</p>
                ) : (
                  filteredIndustries.map((n, i) => (
                    <button
                      key={i}
                      onClick={() => { setIndustrySearch(""); selectNode(n); }}
                      className="w-full text-left text-xs px-2 py-1.5 rounded hover:bg-gray-800 text-gray-300 hover:text-white transition-colors flex items-center justify-between gap-2"
                    >
                      <span className="truncate">{n.name}</span>
                      {n.total_stocks > 0 && <span className="text-gray-600 shrink-0">{n.total_stocks}</span>}
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Sector tree — scrollable independently */}
          <div className="flex-1 overflow-y-auto pb-4 space-y-0.5">
            {sectorsLoading && (
              <div className="flex items-center gap-2 text-gray-500 text-xs py-4 px-2">
                <RefreshCw size={13} className="animate-spin" /> Loading…
              </div>
            )}
            {sectorsError && (
              <div className="text-red-400 text-xs bg-red-900/10 border border-red-800/30 rounded-lg px-3 py-2">
                {sectorsError}
              </div>
            )}
            {sectors.map((s, i) => (
              <SectorRow
                key={s.code}
                sector={s}
                color={SECTOR_COLORS[i % SECTOR_COLORS.length]}
                activeSector={activeSector}
                activePath={activePath}
                onSelectSector={selectSector}
                onSelectNode={selectNode}
              />
            ))}
          </div>
        </div>

        {/* ── Right panel ── */}
        <div className="flex-1 min-w-0">

          {/* Breadcrumb */}
          {activeSectorInfo && (
            <div className="flex items-center gap-1 text-xs text-gray-500 mb-3 flex-wrap">
              <button onClick={() => setSp({})} className="hover:text-white transition-colors">All Sectors</button>
              <ChevronRight size={11} />
              <span
                className={`${!activePath ? "text-white font-medium" : "hover:text-white cursor-pointer transition-colors"}`}
                onClick={() => setSp({ sector: activeSector! })}
              >
                {activeSectorInfo.name}
              </span>
              {activePath && activeNodeName && (
                <>
                  <ChevronRight size={11} />
                  <span className="text-white font-medium">{activeNodeName}</span>
                </>
              )}
            </div>
          )}

          {/* Loading */}
          {pageLoading && (
            <div className="flex items-center justify-center gap-2 text-gray-500 text-sm py-16">
              <RefreshCw size={16} className="animate-spin" /> Loading stocks…
            </div>
          )}

          {/* Error */}
          {pageError && !pageLoading && (
            <div className="text-red-400 text-sm bg-red-900/10 border border-red-800/30 rounded-lg px-4 py-3">
              {pageError}
            </div>
          )}

          {/* AI Sector Pulse — always visible in overview mode */}
          {!activeSector && (
            <SectorPulsePanel
              analysis={pulse}
              loading={pulseLoading}
              error={pulseError}
              onRefresh={() => {
                setPulseLoading(true);
                setPulseError(null);
                marketApi.getSectorAnalysis(true)
                  .then(setPulse)
                  .catch(e => setPulseError(e.message ?? "AI sector analysis unavailable"))
                  .finally(() => setPulseLoading(false));
              }}
            />
          )}

          {/* Overview table — shown when no sector/industry is selected */}
          {!activeSector && !sectorsLoading && (
            overviewLoading ? (
              <div className="flex items-center justify-center gap-2 text-gray-500 text-sm py-16">
                <RefreshCw size={16} className="animate-spin" /> Loading industry overview…
              </div>
            ) : overviewError ? (
              <div className="text-red-400 text-sm bg-red-900/10 border border-red-800/30 rounded-lg px-4 py-3">
                {overviewError}
              </div>
            ) : overview.length > 0 ? (
              <OverviewTable rows={overview} onSelect={selectOverviewRow} />
            ) : (
              <div className="flex flex-col items-center justify-center py-24 text-center">
                <BarChart2 size={44} className="text-gray-700 mb-4" />
                <p className="text-gray-400 text-sm">Select a sector or search an industry on the left.</p>
              </div>
            )
          )}

          {/* Stock table */}
          {page && !pageLoading && (
            <>
              {page.fetched_at && (
                <p className="text-[10px] text-gray-600 mb-2">
                  Cached {Math.round((Date.now() / 1000 - page.fetched_at) / 60)} min ago
                  {page.error && <span className="ml-2 text-yellow-600">· {page.error}</span>}
                </p>
              )}
              <StockTable
                title={page.title}
                stocks={page.stocks}
                onNavigate={sym => navigate(`/stock/${sym}?exchange=NSE`)}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
