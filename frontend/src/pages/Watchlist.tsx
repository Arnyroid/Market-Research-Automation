import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Trash2, TrendingUp, TrendingDown, Search, ChevronUp, ChevronDown, ChevronsUpDown, WifiOff, Clock } from "lucide-react";
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
        {active
          ? dir === "asc"
            ? <ChevronUp size={12} className="text-blue-400" />
            : <ChevronDown size={12} className="text-blue-400" />
          : <ChevronsUpDown size={12} className="text-gray-600" />}
      </span>
    </th>
  );
}

// ── Enriched row type (watchlist item + live prices merged) ───────────────────

interface WatchlistRow extends WatchlistItem {
  ltp: number | null;
  pct_change: number | null;
  abs_change: number | null;
  lastUpdated: number | null;
}

export default function WatchlistPage() {
  const [items, setItems]           = useState<WatchlistItem[]>([]);
  const [restPrices, setRestPrices] = useState<Map<string, Quote>>(new Map());

  // ── Add-form state ──────────────────────────────────────────────────────────
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

  const { prices: livePrices, connected } = usePriceSocket();
  const navigate   = useNavigate();

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

  // ── Close dropdown on outside click ────────────────────────────────────────
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (formRef.current && !formRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  // ── Live search as user types ───────────────────────────────────────────────
  function handleQueryChange(value: string) {
    setQuery(value);
    setSelectedSymbol("");
    setSelectedName("");

    if (searchDebounce.current) clearTimeout(searchDebounce.current);
    if (value.trim().length < 1) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }
    searchDebounce.current = setTimeout(async () => {
      try {
        const results = await watchlistApi.search(value.trim());
        setSuggestions(results);
        setShowSuggestions(results.length > 0);
      } catch {
        setSuggestions([]);
        setShowSuggestions(false);
      }
    }, 250);
  }

  // ── User picks a suggestion ─────────────────────────────────────────────────
  function handleSelect(s: SymbolSearchResult) {
    setQuery(`${s.symbol} — ${s.company_name}`);
    setSelectedSymbol(s.symbol);
    setSelectedName(s.company_name);
    setExchange(s.exchange as "NSE" | "BSE");
    setShowSuggestions(false);
  }

  // ── Submit ──────────────────────────────────────────────────────────────────
  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const sym = (selectedSymbol || query).trim().toUpperCase();
    if (!sym) return;
    setAdding(true); setError(null);
    try {
      const item = await watchlistApi.add({
        symbol: sym,
        exchange,
        company_name: selectedName || undefined,
      });
      setItems(prev => [item, ...prev]);
      setQuery("");
      setSelectedSymbol("");
      setSelectedName("");
      setSuggestions([]);
    } catch (err: any) {
      setError(err.message ?? "Failed to add symbol");
    } finally {
      setAdding(false);
    }
  }

  // ── Delete ──────────────────────────────────────────────────────────────────
  const [removingId, setRemovingId] = useState<number | null>(null);

  async function handleRemove(e: React.MouseEvent, id: number) {
    e.stopPropagation();
    if (removingId !== null) return;
    setRemovingId(id);
    setItems(prev => prev.filter(i => i.id !== id));
    try {
      await watchlistApi.remove(id);
    } catch {
      watchlistApi.list().then(setItems).catch(console.error);
    } finally {
      setRemovingId(null);
    }
  }

  // ── Merge items with live/rest prices into enriched rows ───────────────────
  const enrichedRows: WatchlistRow[] = items.map(item => {
    const key      = `${item.symbol}:${item.exchange}`;
    const liveWs   = livePrices.get(key) ?? null;
    const liveRest = restPrices.get(key) ?? null;
    const live     = liveWs ?? liveRest ?? null;
    const pct      = live?.pct_change ?? null;
    const abs      = live != null && pct != null
      ? parseFloat((live.ltp - live.ltp / (1 + pct / 100)).toFixed(2))
      : null;
    const lastUpdated = liveWs?.lastUpdated ?? null;
    return { ...item, ltp: live?.ltp ?? null, pct_change: pct, abs_change: abs, lastUpdated };
  });

  // ── Sort + filter ───────────────────────────────────────────────────────────
  const [tableFilter, setTableFilter] = useState("");

  const { filtered, sortKey, sortDir, setSort } = useSortFilter(enrichedRows, {
    textKeys: ["symbol", "company_name"],
    getValue: (row, key) => {
      switch (key) {
        case "symbol":      return row.symbol;
        case "company":     return row.company_name ?? row.symbol;
        case "ltp":         return row.ltp ?? -Infinity;
        case "abs_change":  return row.abs_change ?? -Infinity;
        case "pct_change":  return row.pct_change ?? -Infinity;
        default:            return "";
      }
    },
    defaultSortKey: "",
  });

  // Apply the separate table search filter on top of useSortFilter's output
  const displayed = tableFilter.trim()
    ? filtered.filter(r =>
        `${r.symbol} ${r.company_name ?? ""}`.toLowerCase().includes(tableFilter.trim().toLowerCase())
      )
    : filtered;

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Watchlist</h1>
          <p className="text-gray-400 text-sm mt-1">Track NSE &amp; BSE equities with live prices</p>
        </div>
        {items.length > 0 && !connected && (
          <div className="flex items-center gap-1.5 text-xs text-yellow-500/80 bg-yellow-900/20 border border-yellow-800/40 px-3 py-1.5 rounded-lg mt-1">
            <WifiOff size={12} />
            Live feed disconnected — reconnecting…
          </div>
        )}
      </div>

      {/* Add form */}
      <form onSubmit={handleAdd} className="card flex gap-3 mb-6 items-end">
        <div className="flex-1 relative" ref={formRef}>
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
            />
          </div>

          {/* Suggestions dropdown */}
          {showSuggestions && (
            <ul className="absolute z-50 left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-hidden">
              {suggestions.map(s => (
                <li
                  key={s.symbol}
                  onMouseDown={() => handleSelect(s)}
                  className="flex items-center justify-between px-4 py-2.5 hover:bg-gray-800 cursor-pointer group"
                >
                  <div>
                    <span className="font-mono font-semibold text-white text-sm">{s.symbol}</span>
                    <span className="ml-2 text-gray-400 text-sm">{s.company_name}</span>
                  </div>
                  <span className="text-xs bg-gray-800 group-hover:bg-gray-700 text-gray-500 px-1.5 py-px rounded font-medium ml-3 shrink-0">
                    {s.exchange}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Exchange</label>
          <select className="select" value={exchange}
            onChange={e => setExchange(e.target.value as "NSE" | "BSE")}>
            <option>NSE</option>
            <option>BSE</option>
          </select>
        </div>
        <button type="submit" disabled={adding} className="btn-primary">
          <Plus size={15} />
          {adding ? "Adding…" : "Add"}
        </button>
      </form>

      {error && (
        <div className="mb-4 px-4 py-3 bg-red-900/40 border border-red-800 rounded-lg text-red-300 text-sm">{error}</div>
      )}

      {/* Table filter */}
      {items.length > 1 && (
        <div className="mb-3 relative max-w-xs">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            className="input pl-8 text-sm py-2"
            placeholder="Filter watchlist…"
            value={tableFilter}
            onChange={e => setTableFilter(e.target.value)}
          />
        </div>
      )}

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-800/50">
            <tr>
              <SortTh label="Script"   sortKey="company" current={sortKey} dir={sortDir} onSort={setSort} />
              <SortTh label="LTP"      sortKey="ltp"     current={sortKey} dir={sortDir} onSort={setSort} className="text-right" />
              <SortTh label="Change"   sortKey="abs_change" current={sortKey} dir={sortDir} onSort={setSort} className="text-right" />
              <SortTh label="1D %"     sortKey="pct_change" current={sortKey} dir={sortDir} onSort={setSort} className="text-right" />
              <th className="th w-10"></th>
            </tr>
          </thead>
          <tbody>
            {displayed.length === 0 && (
              <tr>
                <td colSpan={5} className="td text-center text-gray-500 py-16">
                  {items.length === 0
                    ? "No symbols yet — search above to add one."
                    : "No results match your filter."}
                </td>
              </tr>
            )}
            {displayed.map(item => {
              const pct  = item.pct_change;
              const isUp = pct != null && pct >= 0;
              const displayName = item.company_name || item.symbol;
              return (
                <tr
                  key={item.id}
                  onClick={() => navigate(`/stock/${item.symbol}?exchange=${item.exchange}`)}
                  className="hover:bg-gray-800/40 cursor-pointer transition-colors"
                >
                  <td className="td">
                    <div className="flex flex-col">
                      <span className="font-semibold text-white">{displayName}</span>
                      <span className="flex items-center gap-1.5 mt-0.5">
                        <span className="font-mono text-xs text-gray-500">{item.symbol}</span>
                        <span className="text-xs bg-gray-800 text-gray-500 px-1.5 py-px rounded font-medium">{item.exchange}</span>
                      </span>
                    </div>
                  </td>
                  <td className="td text-right font-mono text-white">
                    {item.ltp != null ? (
                      <span className="inline-flex items-center justify-end gap-1.5">
                        {item.lastUpdated != null && (Date.now() - item.lastUpdated) > STALE_MS && (
                          <Clock size={11} className="text-yellow-600 shrink-0" title="Price may be stale" />
                        )}
                        ₹{item.ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </span>
                    ) : <span className="text-gray-600">—</span>}
                  </td>
                  <td className={`td text-right font-mono ${item.abs_change != null ? (isUp ? "gain" : "loss") : "text-gray-600"}`}>
                    {item.abs_change != null
                      ? `${isUp ? "+" : ""}₹${Math.abs(item.abs_change).toFixed(2)}`
                      : "—"}
                  </td>
                  <td className={`td text-right font-mono ${pct != null ? (isUp ? "gain" : "loss") : "text-gray-600"}`}>
                    {pct != null ? (
                      <span className="flex items-center justify-end gap-1">
                        {isUp ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                        {isUp ? "+" : ""}{pct.toFixed(2)}%
                      </span>
                    ) : "—"}
                  </td>
                  <td className="td text-right">
                    <button
                      onClick={e => handleRemove(e, item.id)}
                      disabled={removingId === item.id}
                      className="text-gray-600 hover:text-red-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {items.length > 0 && (
        <p className="text-xs text-gray-600 mt-3 text-right flex items-center justify-end gap-1.5">
          {connected
            ? <><span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />Live</>
            : <><WifiOff size={11} className="text-gray-600" />Reconnecting</>}
          {" "}· prices update every 60s during market hours · click a row to view details
        </p>
      )}
    </div>
  );
}
