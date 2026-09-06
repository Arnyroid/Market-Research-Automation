import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus, Trash2, TrendingUp, TrendingDown, Search,
  ChevronUp, ChevronDown, ChevronsUpDown, WifiOff,
  Clock, ChevronRight, X, Bell,
} from "lucide-react";
import { watchlistApi, WatchlistItem, SymbolSearchResult } from "../api/watchlist";
import { pricesApi, Quote } from "../api/prices";
import { usePriceSocket } from "../hooks/usePriceSocket";
import { useSortFilter } from "../hooks/useSortFilter";

/** Price is considered stale when last update was over 10 minutes ago */
const STALE_MS = 10 * 60 * 1000;

// ── Sortable header cell ──────────────────────────────────────────────────────

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
        {/* #10 — inactive indicators are text-gray-500 (brighter than before) */}
        {active
          ? dir === "asc"
            ? <ChevronUp size={12} className="text-blue-400" />
            : <ChevronDown size={12} className="text-blue-400" />
          : <ChevronsUpDown size={12} className="text-gray-500" />}
      </span>
    </th>
  );
}

// ── Day-range mini bar ────────────────────────────────────────────────────────

function DayRangeBar({ low, high, ltp }: { low: number; high: number; ltp: number }) {
  const range = high - low;
  if (range <= 0) return <span className="text-gray-600 text-xs">—</span>;
  const pct = Math.min(100, Math.max(0, ((ltp - low) / range) * 100));
  return (
    <div className="flex flex-col gap-0.5 min-w-[80px]">
      <div className="relative h-1 bg-gray-700 rounded-full overflow-hidden">
        <div className="absolute h-full w-1 bg-blue-400 rounded-full" style={{ left: `calc(${pct}% - 2px)` }} />
      </div>
      <div className="flex justify-between text-[10px] text-gray-600 tabular-nums">
        <span>₹{low.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</span>
        <span>₹{high.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</span>
      </div>
    </div>
  );
}

// ── Enriched row type ─────────────────────────────────────────────────────────

interface WatchlistRow extends WatchlistItem {
  ltp:         number | null;
  pct_change:  number | null;
  abs_change:  number | null;
  lastUpdated: number | null;
  open:        number | null;
  high:        number | null;
  low:         number | null;
  volume:      number | null;
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function WatchlistPage() {
  const [items, setItems]           = useState<WatchlistItem[]>([]);
  const [restPrices, setRestPrices] = useState<Map<string, Quote>>(new Map());

  // ── Add-form state ──────────────────────────────────────────────────────────
  const [showForm, setShowForm]         = useState(false);  // #1 — collapsed by default
  const [query, setQuery]               = useState("");
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [selectedName, setSelectedName]     = useState("");
  const [exchange, setExchange]         = useState<"NSE" | "BSE">("NSE");
  const [suggestions, setSuggestions]   = useState<SymbolSearchResult[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [adding, setAdding]             = useState(false);
  const [error, setError]               = useState<string | null>(null);
  const searchDebounce                  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const formRef                         = useRef<HTMLDivElement>(null);

  // #5 — inline delete confirmation
  const [confirmDelId, setConfirmDelId] = useState<number | null>(null);
  const [removingId, setRemovingId]     = useState<number | null>(null);

  const { prices: livePrices, connected } = usePriceSocket();
  const navigate = useNavigate();

  // ── Load watchlist + pre-fetch prices ──────────────────────────────────────
  useEffect(() => {
    watchlistApi.list().then(loaded => {
      setItems(loaded);
      loaded.forEach(item => {
        pricesApi.getQuote(item.symbol, item.exchange)
          .then(q => {
            setRestPrices(prev => {
              const next = new Map(prev);
              next.set(`${item.symbol}:${item.exchange}`, q);
              return next;
            });
            if (!item.company_name && q.company_name) {
              setItems(prev => prev.map(i =>
                i.id === item.id ? { ...i, company_name: q.company_name } : i
              ));
            }
          })
          .catch(() => {});
      });
    }).catch(console.error);
  }, []);

  // ── Close dropdown + form on outside click ──────────────────────────────────
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (formRef.current && !formRef.current.contains(e.target as Node))
        setShowSuggestions(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  // ── Live search ─────────────────────────────────────────────────────────────
  function handleQueryChange(value: string) {
    setQuery(value);
    setSelectedSymbol("");
    setSelectedName("");
    if (searchDebounce.current) clearTimeout(searchDebounce.current);
    if (value.trim().length < 1) { setSuggestions([]); setShowSuggestions(false); return; }
    searchDebounce.current = setTimeout(async () => {
      try {
        const results = await watchlistApi.search(value.trim());
        setSuggestions(results);
        setShowSuggestions(results.length > 0);
      } catch { setSuggestions([]); setShowSuggestions(false); }
    }, 250);
  }

  function handleSelect(s: SymbolSearchResult) {
    setQuery(`${s.symbol} — ${s.company_name}`);
    setSelectedSymbol(s.symbol);
    setSelectedName(s.company_name);
    setExchange(s.exchange as "NSE" | "BSE");
    setShowSuggestions(false);
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const sym = (selectedSymbol || query).trim().toUpperCase();
    if (!sym) return;
    setAdding(true); setError(null);
    try {
      const item = await watchlistApi.add({ symbol: sym, exchange, company_name: selectedName || undefined });
      setItems(prev => [item, ...prev]);
      setQuery(""); setSelectedSymbol(""); setSelectedName(""); setSuggestions([]);
      setShowForm(false);  // collapse form on successful add
    } catch (err: any) {
      setError(err.message ?? "Failed to add symbol");
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(id: number) {
    if (removingId !== null) return;
    setRemovingId(id);
    setConfirmDelId(null);
    setItems(prev => prev.filter(i => i.id !== id));
    try {
      await watchlistApi.remove(id);
    } catch {
      watchlistApi.list().then(setItems).catch(console.error);
    } finally {
      setRemovingId(null);
    }
  }

  // ── Merge items with live/rest prices ──────────────────────────────────────
  const enrichedRows: WatchlistRow[] = items.map(item => {
    const key      = `${item.symbol}:${item.exchange}`;
    const liveWs   = livePrices.get(key) ?? null;
    const liveRest = restPrices.get(key) ?? null;
    const live     = liveWs ?? liveRest ?? null;
    const pct      = live?.pct_change ?? null;
    const abs      = live != null && pct != null
      ? parseFloat((live.ltp - live.ltp / (1 + pct / 100)).toFixed(2))
      : null;
    return {
      ...item,
      ltp:         live?.ltp ?? null,
      pct_change:  pct,
      abs_change:  abs,
      lastUpdated: liveWs?.lastUpdated ?? null,
      open:        liveRest?.open   ?? null,
      high:        liveRest?.high   ?? null,
      low:         liveRest?.low    ?? null,
      volume:      liveRest?.volume ?? null,
    };
  });

  // ── Sort + filter ────────────────────────────────────────────────────────────
  const [tableFilter, setTableFilter] = useState("");

  const { filtered, sortKey, sortDir, setSort } = useSortFilter(enrichedRows, {
    textKeys: ["symbol", "company_name"],
    getValue: (row, key) => {
      switch (key) {
        case "symbol":     return row.symbol;
        case "company":    return row.company_name ?? row.symbol;
        case "ltp":        return row.ltp        ?? -Infinity;
        case "abs_change": return row.abs_change  ?? -Infinity;
        case "pct_change": return row.pct_change  ?? -Infinity;
        case "volume":     return row.volume      ?? -Infinity;
        default:           return "";
      }
    },
    defaultSortKey: "",
    numericKeys: ["ltp", "abs_change", "pct_change", "volume"],
  });

  const displayed = tableFilter.trim()
    ? filtered.filter(r =>
        `${r.symbol} ${r.company_name ?? ""}`.toLowerCase().includes(tableFilter.trim().toLowerCase())
      )
    : filtered;

  // ── #8 Header stats ──────────────────────────────────────────────────────────
  const gaining  = enrichedRows.filter(r => (r.pct_change ?? 0) > 0).length;
  const declining = enrichedRows.filter(r => (r.pct_change ?? 0) < 0).length;
  const flat     = enrichedRows.filter(r => r.pct_change != null && r.pct_change === 0).length;

  return (
    <div className="p-8 max-w-5xl mx-auto">

      {/* ── Header ── */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Watchlist</h1>
          {/* #8 — stat bar */}
          {items.length > 0 ? (
            <div className="flex items-center gap-3 mt-1 text-sm">
              <span className="text-gray-400">{items.length} symbol{items.length !== 1 ? "s" : ""}</span>
              {gaining  > 0 && <span className="text-emerald-400">▲ {gaining} gaining</span>}
              {declining > 0 && <span className="text-red-400">▼ {declining} declining</span>}
              {flat     > 0 && <span className="text-gray-500">● {flat} flat</span>}
            </div>
          ) : (
            <p className="text-gray-400 text-sm mt-1">Track NSE &amp; BSE equities with live prices</p>
          )}
        </div>
        <div className="flex items-center gap-2 mt-1">
          {items.length > 0 && !connected && (
            <div className="flex items-center gap-1.5 text-xs text-yellow-500/80 bg-yellow-900/20 border border-yellow-800/40 px-3 py-1.5 rounded-lg">
              <WifiOff size={12} /> Disconnected
            </div>
          )}
          {/* #1 — collapsed form toggle */}
          <button
            onClick={() => { setShowForm(v => !v); setError(null); }}
            className={`btn-primary flex items-center gap-1.5 text-sm ${showForm ? "bg-gray-700 hover:bg-gray-600" : ""}`}
          >
            {showForm ? <X size={14} /> : <Plus size={14} />}
            {showForm ? "Cancel" : "Add Symbol"}
          </button>
        </div>
      </div>

      {/* ── Add form (collapsible) ── */}
      {showForm && (
        <form onSubmit={handleAdd} className="card mb-5 space-y-3">
          <div className="flex gap-3 items-end" ref={formRef}>
            {/* Search input */}
            <div className="flex-1 relative">
              <label className="block text-xs text-gray-400 mb-1.5">Symbol</label>
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  className="input pl-8"
                  placeholder="Search by name or symbol, e.g. Reliance or AXISBANK"
                  value={query}
                  onChange={e => handleQueryChange(e.target.value)}
                  onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                  autoComplete="off"
                  autoFocus
                />
              </div>
              {showSuggestions && (
                <ul className="absolute z-50 left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-hidden max-h-52 overflow-y-auto">
                  {suggestions.map(s => (
                    <li key={s.symbol} onMouseDown={() => handleSelect(s)}
                      className="flex items-center justify-between px-4 py-2.5 hover:bg-gray-800 cursor-pointer group">
                      <div>
                        <span className="font-mono font-semibold text-white text-sm">{s.symbol}</span>
                        <span className="ml-2 text-gray-400 text-sm">{s.company_name}</span>
                      </div>
                      <span className="text-xs bg-gray-800 group-hover:bg-gray-700 text-gray-500 px-1.5 py-px rounded ml-3 shrink-0">
                        {s.exchange}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* #7 — Exchange as toggle chip */}
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Exchange</label>
              <div className="flex rounded-lg border border-gray-700 overflow-hidden text-xs font-medium">
                {(["NSE", "BSE"] as const).map(ex => (
                  <button
                    key={ex} type="button"
                    onClick={() => setExchange(ex)}
                    className={`px-3 py-2 transition-colors ${
                      exchange === ex
                        ? "bg-blue-600 text-white"
                        : "bg-gray-800 text-gray-400 hover:text-white"
                    }`}
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>

            <button type="submit" disabled={adding} className="btn-primary self-end">
              <Plus size={15} />
              {adding ? "Adding…" : "Add"}
            </button>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-300 text-xs bg-red-900/20 border border-red-800/30 rounded px-3 py-2">
              <X size={12} /> {error}
            </div>
          )}
        </form>
      )}

      {/* ── Filter + sort bar (#6 — shows at > 0) ── */}
      {items.length > 0 && (
        <div className="flex items-center gap-2 mb-4">
          <div className="relative flex-1 max-w-xs">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              className="input pl-8 text-sm py-1.5 w-full"
              placeholder="Filter watchlist…"
              value={tableFilter}
              onChange={e => setTableFilter(e.target.value)}
            />
          </div>
          {tableFilter && (
            <button onClick={() => setTableFilter("")}
              className="btn-ghost p-1.5 text-gray-500 hover:text-white">
              <X size={13} />
            </button>
          )}
          <span className="text-xs text-gray-600 ml-auto">
            {displayed.length} of {items.length}
          </span>
        </div>
      )}

      {/* ── Table ── */}
      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-800/50">
            <tr>
              <SortTh label="Script"  sortKey="company"    current={sortKey} dir={sortDir} onSort={setSort} />
              <SortTh label="LTP"     sortKey="ltp"        current={sortKey} dir={sortDir} onSort={setSort} className="text-right" />
              <SortTh label="Change"  sortKey="abs_change" current={sortKey} dir={sortDir} onSort={setSort} className="text-right" />
              <SortTh label="1D %"    sortKey="pct_change" current={sortKey} dir={sortDir} onSort={setSort} className="text-right" />
              {/* #2 — new columns */}
              <th className="th text-right whitespace-nowrap hidden lg:table-cell">Day Range</th>
              <SortTh label="Volume"  sortKey="volume"     current={sortKey} dir={sortDir} onSort={setSort} className="text-right hidden lg:table-cell" />
              <th className="th w-24 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {/* #4 — rich empty state */}
            {displayed.length === 0 && (
              <tr>
                <td colSpan={7} className="td text-center py-16">
                  {items.length === 0 ? (
                    <div className="space-y-2">
                      <p className="text-gray-400 font-medium">Your watchlist is empty</p>
                      <p className="text-gray-600 text-xs">
                        Click <span className="text-blue-400 font-medium">Add Symbol</span> above and search for{" "}
                        <span className="font-mono text-gray-400">RELIANCE</span>,{" "}
                        <span className="font-mono text-gray-400">HDFCBANK</span>,{" "}
                        <span className="font-mono text-gray-400">INFY</span>…
                      </p>
                    </div>
                  ) : (
                    <p className="text-gray-500 text-sm">No results match "<span className="text-gray-400">{tableFilter}</span>"</p>
                  )}
                </td>
              </tr>
            )}

            {displayed.map(item => {
              const pct    = item.pct_change;
              const isUp   = pct != null && pct >= 0;
              const name   = item.company_name || item.symbol;
              const isStale = item.lastUpdated != null && (Date.now() - item.lastUpdated) > STALE_MS;
              const hasRange = item.high != null && item.low != null && item.ltp != null;
              const isDeleting = confirmDelId === item.id;

              return (
                <tr
                  key={item.id}
                  onClick={() => !isDeleting && navigate(`/stock/${item.symbol}?exchange=${item.exchange}`)}
                  className={`border-t border-gray-800/60 transition-colors group ${
                    isDeleting ? "bg-red-900/10" : "hover:bg-gray-800/40 cursor-pointer"
                  }`}
                >
                  {/* Script */}
                  <td className="td">
                    <div className="flex flex-col">
                      <span className="font-semibold text-white">{name}</span>
                      <span className="flex items-center gap-1.5 mt-0.5">
                        <span className="font-mono text-xs text-gray-500">{item.symbol}</span>
                        <span className="text-xs bg-gray-800 text-gray-500 px-1.5 py-px rounded font-medium">{item.exchange}</span>
                      </span>
                    </div>
                  </td>

                  {/* LTP */}
                  <td className="td text-right font-mono text-white">
                    {item.ltp != null ? (
                      <span className="inline-flex items-center justify-end gap-1.5">
                        {isStale && <Clock size={11} className="text-yellow-600 shrink-0" title="Price may be stale" />}
                        ₹{item.ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </span>
                    ) : <span className="text-gray-600">—</span>}
                  </td>

                  {/* Abs change */}
                  <td className={`td text-right font-mono ${item.abs_change != null ? (isUp ? "gain" : "loss") : "text-gray-600"}`}>
                    {item.abs_change != null
                      ? `${isUp ? "+" : ""}₹${Math.abs(item.abs_change).toFixed(2)}`
                      : "—"}
                  </td>

                  {/* % change */}
                  <td className={`td text-right font-mono ${pct != null ? (isUp ? "gain" : "loss") : "text-gray-600"}`}>
                    {pct != null ? (
                      <span className="flex items-center justify-end gap-1">
                        {isUp ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                        {isUp ? "+" : ""}{pct.toFixed(2)}%
                      </span>
                    ) : "—"}
                  </td>

                  {/* #2 — Day range bar */}
                  <td className="td hidden lg:table-cell">
                    <div className="flex justify-end">
                      {hasRange
                        ? <DayRangeBar low={item.low!} high={item.high!} ltp={item.ltp!} />
                        : <span className="text-gray-600 text-xs">—</span>}
                    </div>
                  </td>

                  {/* #2 — Volume */}
                  <td className="td text-right font-mono text-gray-400 hidden lg:table-cell">
                    {item.volume != null
                      ? item.volume >= 1_000_000
                        ? `${(item.volume / 1_000_000).toFixed(1)}M`
                        : item.volume >= 1_000
                          ? `${(item.volume / 1_000).toFixed(0)}K`
                          : item.volume.toString()
                      : <span className="text-gray-600">—</span>}
                  </td>

                  {/* Actions — #5 delete confirmation, #9 arrow affordance */}
                  <td className="td text-right" onClick={e => e.stopPropagation()}>
                    {isDeleting ? (
                      <span className="inline-flex items-center gap-1.5">
                        <span className="text-[10px] text-red-400 whitespace-nowrap">Remove?</span>
                        <button
                          onClick={() => handleRemove(item.id)}
                          className="text-[10px] font-semibold text-red-400 hover:text-red-300 px-1.5 py-0.5 rounded bg-red-900/30 border border-red-800/40"
                        >Yes</button>
                        <button
                          onClick={() => setConfirmDelId(null)}
                          className="text-gray-500 hover:text-gray-300 p-0.5"
                        ><X size={11} /></button>
                      </span>
                    ) : (
                      <span className="inline-flex items-center justify-end gap-1">
                        {/* Bell quick-action */}
                        <button
                          onClick={e => { e.stopPropagation(); navigate(`/alerts?symbol=${item.symbol}&exchange=${item.exchange}`); }}
                          title="Create alert"
                          className="text-gray-600 hover:text-blue-400 transition-colors p-1 opacity-0 group-hover:opacity-100"
                        ><Bell size={13} /></button>
                        {/* Delete */}
                        <button
                          onClick={() => setConfirmDelId(item.id)}
                          disabled={removingId === item.id}
                          className="text-gray-600 hover:text-red-400 transition-colors p-1 disabled:opacity-40"
                          title="Remove"
                        ><Trash2 size={13} /></button>
                        {/* #9 — click affordance */}
                        <ChevronRight size={13} className="text-gray-700 group-hover:text-gray-500 transition-colors shrink-0" />
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* ── Footer status bar ── */}
      {items.length > 0 && (
        <p className="text-xs text-gray-600 mt-3 text-right flex items-center justify-end gap-1.5">
          {connected
            ? <><span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />Live</>
            : <><WifiOff size={11} className="text-gray-600" />Reconnecting</>}
          {" "}· prices update every 60s during market hours · click row to view details
        </p>
      )}
    </div>
  );
}
