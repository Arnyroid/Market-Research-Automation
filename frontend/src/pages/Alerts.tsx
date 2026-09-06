import React, { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Plus, BellOff, Bell, Trash2, Repeat2, ChevronDown, ChevronUp,
  Search, ArrowUpDown, ChevronRight, AlertTriangle, X,
} from "lucide-react";
import { alertsApi, Alert, AlertLog, CreateAlertPayload } from "../api/alerts";
import { watchlistApi, SymbolSearchResult } from "../api/watchlist";
import { pricesApi } from "../api/prices";

// ── Condition metadata ─────────────────────────────────────────────────────────

const CONDITIONS = [
  { value: "price_above",         label: "Price rises above",        unit: "₹", pill: "↑ Above",     pillCls: "bg-emerald-900/40 text-emerald-400 border-emerald-800/50" },
  { value: "price_below",         label: "Price drops below",        unit: "₹", pill: "↓ Below",     pillCls: "bg-red-900/40    text-red-400    border-red-800/50"     },
  { value: "pct_change_up",       label: "1-day gain exceeds",       unit: "%", pill: "% Up",        pillCls: "bg-emerald-900/40 text-emerald-400 border-emerald-800/50" },
  { value: "pct_change_down",     label: "1-day drop exceeds",       unit: "%", pill: "% Down",      pillCls: "bg-red-900/40    text-red-400    border-red-800/50"     },
  { value: "portfolio_pnl_below", label: "Portfolio P&L drops below", unit: "%", pill: "P&L ↓",      pillCls: "bg-yellow-900/40 text-yellow-400 border-yellow-800/50"  },
];

function conditionMeta(type: string) {
  return CONDITIONS.find(x => x.value === type) ?? CONDITIONS[0];
}

function conditionLabel(type: string, threshold: number) {
  const c = conditionMeta(type);
  return `${c.label} ${c.unit === "%" ? `${threshold}%` : `₹${threshold.toLocaleString("en-IN")}` }`;
}

// ── Alert card ─────────────────────────────────────────────────────────────────

function AlertCard({
  alert, onToggle, onDelete, isWatched,
}: {
  alert: Alert; onToggle: () => void; onDelete: () => void; isWatched: boolean;
}) {
  const [ltp, setLtp]               = useState<number | null>(null);
  const [logs, setLogs]             = useState<AlertLog[]>([]);
  const [showLogs, setShowLogs]     = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);

  useEffect(() => {
    pricesApi.getQuote(alert.symbol, alert.exchange)
      .then(q => setLtp(q.ltp))
      .catch(() => {});
  }, [alert.symbol, alert.exchange]);

  async function toggleLogs() {
    if (!showLogs && logs.length === 0) {
      const l = await alertsApi.getLogs(alert.id).catch(() => []);
      setLogs(l);
    }
    setShowLogs(v => !v);
  }

  const meta     = conditionMeta(alert.condition_type);
  const isPct    = alert.condition_type.includes("pct");
  const isAbove  = alert.condition_type === "price_above" || alert.condition_type === "pct_change_up";

  // Progress toward trigger (price-type alerts only)
  const progress = useMemo(() => {
    if (ltp == null || isPct) return null;
    // How far between ltp and threshold (capped 0–100%)
    if (isAbove) {
      // target above current: 0% = far away, 100% = at target
      return Math.min(100, Math.max(0, (ltp / alert.threshold) * 100));
    } else {
      // target below current: 0% = far away, 100% = at target
      return Math.min(100, Math.max(0, (alert.threshold / ltp) * 100));
    }
  }, [ltp, alert.threshold, isPct, isAbove]);

  const distance = ltp != null && !isPct
    ? ((alert.threshold - ltp) / ltp * 100)
    : null;
  const distLabel = distance != null
    ? `${Math.abs(distance).toFixed(1)}% ${distance > 0 ? "away ↑" : "away ↓"}`
    : null;

  // Last trigger time from logs (if already loaded)
  const lastTrigger = logs.length > 0
    ? new Date(logs[0].triggered_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })
    : null;

  const cardOpacity = !alert.active ? "opacity-60" : "";

  return (
    <div className={`card p-0 overflow-hidden transition-opacity ${cardOpacity}`}>
      {/* Progress bar — fills as price approaches threshold */}
      {progress != null && alert.active && (
        <div className="h-0.5 bg-gray-800 w-full">
          <div
            className={`h-full transition-all ${isAbove ? "bg-emerald-500/70" : "bg-red-500/70"}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      <div className="flex items-center justify-between px-4 py-3.5 gap-3">

        {/* Condition pill */}
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border shrink-0 ${meta.pillCls}`}>
          {meta.pill}
        </span>

        {/* Symbol + condition text */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="font-mono font-semibold text-white text-sm">{alert.symbol}</span>
            <span className="text-[10px] bg-gray-800 text-gray-500 px-1.5 py-px rounded">{alert.exchange}</span>
            {alert.repeating && (
              <span className="flex items-center gap-0.5 text-[10px] text-violet-400 bg-violet-900/30 px-1.5 py-px rounded border border-violet-800/40">
                <Repeat2 size={9} /> Repeat
              </span>
            )}
            {alert.active && !isWatched && (
              <span
                className="flex items-center gap-0.5 text-[10px] text-amber-400 bg-amber-900/30 px-1.5 py-px rounded border border-amber-800/40"
                title="This symbol is not on your Watchlist — the price poller won't evaluate this alert until you add it."
              >
                <AlertTriangle size={9} /> Not monitored
              </span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-0.5">{conditionLabel(alert.condition_type, alert.threshold)}</p>
          {alert.notes && <p className="text-[11px] text-gray-600 mt-0.5 italic truncate">{alert.notes}</p>}
          {lastTrigger && (
            <p className="text-[10px] text-gray-600 mt-0.5">Last fired: {lastTrigger}</p>
          )}
        </div>

        {/* LTP + distance */}
        {ltp != null && (
          <div className="text-right shrink-0 hidden sm:block">
            <p className="font-mono text-sm text-white">₹{ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</p>
            {distLabel && (
              <p className={`text-xs mt-0.5 ${isAbove ? "text-emerald-500" : "text-red-400"}`}>{distLabel}</p>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-0.5 shrink-0">
          <button onClick={toggleLogs} title="Trigger history"
            className="btn-ghost p-1.5 hover:text-blue-400">
            {showLogs ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          <button onClick={onToggle} title={alert.active ? "Pause" : "Re-enable"}
            className={`btn-ghost p-1.5 ${alert.active ? "hover:text-yellow-400" : "hover:text-emerald-400"}`}>
            {alert.active ? <BellOff size={14} /> : <Bell size={14} />}
          </button>
          {/* Delete with inline confirmation */}
          {confirmDel ? (
            <span className="flex items-center gap-1 ml-1">
              <span className="text-[10px] text-red-400 whitespace-nowrap">Delete?</span>
              <button onClick={onDelete}
                className="text-[10px] font-semibold text-red-400 hover:text-red-300 px-1.5 py-0.5 rounded bg-red-900/30 border border-red-800/40">
                Yes
              </button>
              <button onClick={() => setConfirmDel(false)}
                className="p-0.5 text-gray-500 hover:text-gray-300">
                <X size={12} />
              </button>
            </span>
          ) : (
            <button onClick={() => setConfirmDel(true)}
              className="btn-ghost p-1.5 hover:text-red-400">
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Trigger log */}
      {showLogs && (
        <div className="border-t border-gray-800/60 bg-gray-900/40 px-4 py-3">
          {logs.length === 0 ? (
            <p className="text-xs text-gray-600 text-center py-1">No triggers recorded yet.</p>
          ) : (
            <div className="space-y-1.5">
              <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2">Trigger history</p>
              {logs.slice(0, 5).map(l => (
                <div key={l.id} className="flex items-center justify-between text-xs gap-3">
                  <span className="text-gray-500 shrink-0">
                    {new Date(l.triggered_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}
                  </span>
                  <span className="font-mono text-gray-300">
                    ₹{l.price_at_trigger.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                  <span className={`shrink-0 ${l.notified ? "text-emerald-500" : "text-gray-600"}`}>
                    {l.notified
                      ? "Notified ✓"
                      : <span title="Check that NTFY_TOPIC is set correctly in your .env">Not sent ⓘ</span>}
                  </span>
                </div>
              ))}
              {logs.length > 5 && (
                <p className="text-[10px] text-gray-600 pt-1">+{logs.length - 5} more triggers</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Paused re-enable CTA — visible on inactive cards */}
      {!alert.active && (
        <div className="border-t border-gray-800/40 px-4 py-2 flex items-center justify-between bg-gray-800/20">
          <span className="text-[11px] text-gray-600">Alert is paused</span>
          <button
            onClick={onToggle}
            className="text-[11px] text-emerald-400 hover:text-emerald-300 font-medium flex items-center gap-1 transition-colors"
          >
            <Bell size={11} /> Re-enable
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function AlertsPage() {
  const [sp] = useSearchParams();

  const [alerts, setAlerts]     = useState<Alert[]>([]);
  const [creating, setCreating] = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [alertFilter, setAlertFilter] = useState("");
  const [alertSort, setAlertSort] = useState<"symbol" | "threshold" | "condition" | "active">("active");

  // Form collapsed by default (#1)
  const [showForm, setShowForm] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Form state — initialise from URL params when navigated from StockDetail
  const prefillSymbol   = sp.get("symbol")?.toUpperCase() ?? "";
  const prefillExchange = sp.get("exchange")?.toUpperCase() ?? "NSE";

  const [query, setQuery]             = useState(prefillSymbol);
  const [selSymbol, setSelSymbol]     = useState(prefillSymbol);
  const [selExchange, setSelExchange] = useState(prefillExchange);
  const [suggestions, setSuggestions] = useState<SymbolSearchResult[]>([]);
  const [showSug, setShowSug]         = useState(false);
  const [condition, setCondition]     = useState("price_above");
  const [threshold, setThreshold]     = useState("");
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [repeating, setRepeating]     = useState(false);
  const [notes, setNotes]             = useState("");
  const [fetchingPrice, setFetchingPrice] = useState(false);

  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dropRef  = useRef<HTMLDivElement>(null);

  // Set of "SYMBOL:EXCHANGE" keys currently on the watchlist — used to warn
  // about alerts whose symbol isn't being polled by the price poller
  const [watchedKeys, setWatchedKeys] = useState<Set<string>>(new Set());

  useEffect(() => {
    alertsApi.list().then(setAlerts).catch(console.error);
    watchlistApi.list()
      .then(items => setWatchedKeys(new Set(items.map(i => `${i.symbol}:${i.exchange}`))))
      .catch(() => null);
  }, []);

  // Auto-open form + pre-fill price when navigated from StockDetail
  useEffect(() => {
    if (!prefillSymbol) return;
    setShowForm(true);
    setFetchingPrice(true);
    pricesApi.getQuote(prefillSymbol, prefillExchange)
      .then(q => { if (q?.ltp) { setThreshold(q.ltp.toFixed(2)); setCurrentPrice(q.ltp); } })
      .catch(() => {})
      .finally(() => setFetchingPrice(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function h(e: MouseEvent) {
      if (dropRef.current && !dropRef.current.contains(e.target as Node)) setShowSug(false);
    }
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  function handleQueryChange(v: string) {
    setQuery(v); setSelSymbol(""); setCurrentPrice(null);
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
    setSelSymbol(s.symbol);
    setSelExchange(s.exchange);
    setShowSug(false);
    if (!condition.includes("pct")) {
      setFetchingPrice(true);
      try {
        const q = await pricesApi.getQuote(s.symbol, s.exchange);
        if (q?.ltp) { setThreshold(q.ltp.toFixed(2)); setCurrentPrice(q.ltp); }
      } catch {} finally { setFetchingPrice(false); }
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const sym = (selSymbol || query).trim().toUpperCase();
    if (!sym || !threshold) { setError("Symbol and threshold are required."); return; }
    setCreating(true); setError(null);
    try {
      const a = await alertsApi.create({
        symbol: sym, exchange: selExchange,
        condition_type: condition as CreateAlertPayload["condition_type"],
        threshold: parseFloat(threshold), repeating,
        notes: notes || undefined,
      } as any);
      setAlerts(prev => [a, ...prev]);
      setQuery(""); setSelSymbol(""); setThreshold(""); setNotes("");
      setRepeating(false); setCurrentPrice(null); setShowForm(false);
    } catch (err: any) { setError(err.message); }
    finally { setCreating(false); }
  }

  async function toggle(id: number, active: boolean) {
    const a = await alertsApi.update(id, { active: !active });
    setAlerts(prev => prev.map(x => x.id === id ? a : x));
  }

  function remove(id: number) {
    // Optimistic: remove from state immediately, then confirm with API
    setAlerts(prev => prev.filter(x => x.id !== id));
    alertsApi.remove(id).catch(() => {
      // Restore on failure by reloading
      alertsApi.list().then(setAlerts).catch(console.error);
    });
  }

  const unit = conditionMeta(condition).unit;

  const sortedAlerts = useMemo(() => {
    const q = alertFilter.trim().toLowerCase();
    const filtered = q
      ? alerts.filter(a =>
          a.symbol.toLowerCase().includes(q) ||
          (a.notes ?? "").toLowerCase().includes(q) ||
          a.condition_type.toLowerCase().includes(q)
        )
      : alerts;
    return [...filtered].sort((a, b) => {
      if (alertSort === "symbol")    return a.symbol.localeCompare(b.symbol);
      if (alertSort === "threshold") return a.threshold - b.threshold;
      if (alertSort === "condition") return a.condition_type.localeCompare(b.condition_type);
      if (a.active !== b.active) return a.active ? -1 : 1;
      return a.symbol.localeCompare(b.symbol);
    });
  }, [alerts, alertFilter, alertSort]);

  const active   = sortedAlerts.filter(a =>  a.active);
  const inactive = sortedAlerts.filter(a => !a.active);

  // Active alerts whose symbol is not in the watchlist
  const unwatchedActive = active.filter(
    a => !watchedKeys.has(`${a.symbol}:${a.exchange}`)
  );

  return (
    <div className="p-8 max-w-3xl mx-auto">

      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Alerts</h1>
          <p className="text-gray-400 text-sm mt-0.5">
            ntfy push notifications · {alerts.length} alert{alerts.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          onClick={() => setShowForm(v => !v)}
          className={`btn-primary flex items-center gap-1.5 text-sm ${showForm ? "bg-gray-700 hover:bg-gray-600" : ""}`}
        >
          {showForm ? <X size={14} /> : <Plus size={14} />}
          {showForm ? "Cancel" : "New Alert"}
        </button>
      </div>

      {/* ── "Not monitored" banner ── */}
      {unwatchedActive.length > 0 && (
        <div className="mb-5 flex items-start gap-3 bg-amber-900/20 border border-amber-700/40 rounded-xl px-4 py-3">
          <AlertTriangle size={15} className="text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-300">
              {unwatchedActive.length === 1
                ? "1 alert won't fire — symbol not on Watchlist"
                : `${unwatchedActive.length} alerts won't fire — symbols not on Watchlist`}
            </p>
            <p className="text-xs text-amber-200/60 mt-0.5">
              The price poller only checks symbols on your Watchlist.{" "}
              <span className="font-medium text-amber-300">
                {unwatchedActive.map(a => `${a.symbol} (${a.exchange})`).join(", ")}
              </span>{" "}
              — add {unwatchedActive.length === 1 ? "it" : "them"} to your Watchlist to activate monitoring.
            </p>
          </div>
        </div>
      )}

      {/* ── Create form (collapsible) ── */}
      {showForm && (
        <form onSubmit={handleCreate} className="card mb-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-200">New Alert</h2>

          {/* Symbol search */}
          <div ref={dropRef} className="relative">
            <label className="block text-xs text-gray-400 mb-1.5">Symbol</label>
            <div className="relative">
              <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input className="input pl-8" placeholder="Search symbol or company name…"
                value={query} onChange={e => handleQueryChange(e.target.value)}
                onFocus={() => suggestions.length > 0 && setShowSug(true)}
                autoComplete="off" />
            </div>
            {showSug && (
              <ul className="absolute z-50 left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-hidden max-h-52 overflow-y-auto">
                {suggestions.map(s => (
                  <li key={s.symbol} onMouseDown={() => handleSelect(s)}
                    className="flex items-center justify-between px-4 py-2.5 hover:bg-gray-800 cursor-pointer">
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

          {/* Condition + Exchange in one row (#5) */}
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label className="block text-xs text-gray-400 mb-1.5">Condition</label>
              <select className="select w-full" value={condition}
                onChange={e => { setCondition(e.target.value); setThreshold(""); setCurrentPrice(null); }}>
                {CONDITIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Exchange</label>
              <select className="select w-full" value={selExchange}
                onChange={e => setSelExchange(e.target.value)}>
                <option>NSE</option><option>BSE</option>
              </select>
            </div>
          </div>

          {/* Threshold with live price reference (#5) */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs text-gray-400">
                Threshold ({unit === "%" ? "%" : "₹"})
              </label>
              {fetchingPrice && <span className="text-[11px] text-gray-600">fetching price…</span>}
              {currentPrice != null && !fetchingPrice && (
                <span className="text-[11px] text-gray-500">
                  Current: <span className="font-mono text-gray-300">₹{currentPrice.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                  {threshold && parseFloat(threshold) !== currentPrice && (
                    <span className={`ml-1.5 font-mono ${parseFloat(threshold) > currentPrice ? "text-emerald-500" : "text-red-400"}`}>
                      → {parseFloat(threshold) > currentPrice ? "+" : ""}{((parseFloat(threshold) - currentPrice) / currentPrice * 100).toFixed(1)}%
                    </span>
                  )}
                </span>
              )}
            </div>
            <input className={`input ${fetchingPrice ? "opacity-50" : ""}`}
              type="number" step="0.01" min="0"
              placeholder={unit === "%" ? "5.0" : "1300.00"}
              value={threshold} onChange={e => setThreshold(e.target.value)}
              disabled={fetchingPrice} />
          </div>

          {/* Repeating toggle — fixed wrapping (#9) */}
          <label className="flex items-center gap-3 cursor-pointer select-none">
            <div onClick={() => setRepeating(v => !v)}
              className={`w-9 h-5 rounded-full transition-colors relative shrink-0 ${repeating ? "bg-violet-600" : "bg-gray-700"}`}>
              <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${repeating ? "translate-x-4" : "translate-x-0.5"}`} />
            </div>
            <div className="min-w-0">
              <span className="text-sm text-gray-300">Repeating</span>
              <p className="text-[11px] text-gray-600 mt-0.5">Fires every poll cycle while condition holds. Default: fires once then pauses.</p>
            </div>
          </label>

          {/* Advanced toggle — Notes behind it (#5) */}
          <button type="button"
            onClick={() => setShowAdvanced(v => !v)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors">
            <ChevronRight size={12} className={`transition-transform ${showAdvanced ? "rotate-90" : ""}`} />
            Advanced
          </button>
          {showAdvanced && (
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Notes <span className="text-gray-600">(optional)</span></label>
              <input className="input" placeholder="e.g. earnings breakout, support level…"
                value={notes} onChange={e => setNotes(e.target.value)} />
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 text-red-400 text-xs bg-red-900/20 border border-red-800/30 rounded px-3 py-2">
              <AlertTriangle size={13} /> {error}
            </div>
          )}

          <button type="submit" disabled={creating} className="btn-primary w-full justify-center">
            <Plus size={15} /> {creating ? "Creating…" : "Create Alert"}
          </button>
        </form>
      )}

      {/* ── Sort + filter bar — shown whenever alerts exist (#8) ── */}
      {alerts.length > 0 && (
        <div className="flex items-center gap-2 mb-5">
          <div className="flex items-center gap-1.5 text-xs text-gray-500 shrink-0">
            <ArrowUpDown size={12} />
            <select className="select text-xs py-1.5 pr-6" value={alertSort}
              onChange={e => setAlertSort(e.target.value as typeof alertSort)}>
              <option value="active">Active first</option>
              <option value="symbol">Symbol A–Z</option>
              <option value="threshold">Threshold ↑</option>
              <option value="condition">Condition type</option>
            </select>
          </div>
          <div className="relative flex-1">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input className="input pl-8 text-sm py-1.5 w-full"
              placeholder="Filter by symbol, condition, notes…"
              value={alertFilter} onChange={e => setAlertFilter(e.target.value)} />
          </div>
          {alertFilter && (
            <button onClick={() => setAlertFilter("")}
              className="btn-ghost p-1.5 text-gray-500 hover:text-white shrink-0">
              <X size={13} />
            </button>
          )}
        </div>
      )}

      {/* ── Active alerts ── */}
      {active.length > 0 && (
        <div className="mb-6">
          <h2 className="flex items-center gap-2 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Active
            <span className="bg-blue-600 text-white text-xs px-1.5 py-0.5 rounded-full font-normal">{active.length}</span>
          </h2>
          <div className="space-y-2">
            {active.map(a => (
              <AlertCard key={a.id} alert={a}
                onToggle={() => toggle(a.id, a.active)}
                onDelete={() => remove(a.id)}
                isWatched={watchedKeys.has(`${a.symbol}:${a.exchange}`)} />
            ))}
          </div>
        </div>
      )}

      {/* ── Paused / Fired alerts — visually distinct (#6) ── */}
      {inactive.length > 0 && (
        <div>
          <h2 className="flex items-center gap-2 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Paused / Fired
            <span className="bg-gray-700 text-gray-400 text-xs px-1.5 py-0.5 rounded-full font-normal">{inactive.length}</span>
          </h2>
          <div className="space-y-2 opacity-75">
            {inactive.map(a => (
              <AlertCard key={a.id} alert={a}
                onToggle={() => toggle(a.id, a.active)}
                onDelete={() => remove(a.id)}
                isWatched={watchedKeys.has(`${a.symbol}:${a.exchange}`)} />
            ))}
          </div>
        </div>
      )}

      {/* No-filter empty state */}
      {alertFilter && active.length === 0 && inactive.length === 0 && (
        <p className="text-xs text-gray-600 py-4 text-center">No alerts match "{alertFilter}".</p>
      )}

      {/* Zero alerts empty state */}
      {alerts.length === 0 && (
        <div className="card text-center py-16">
          <Bell size={32} className="text-gray-700 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">No alerts yet.</p>
          <p className="text-gray-600 text-xs mt-1">
            Click <span className="font-semibold text-gray-400">New Alert</span> above to get started.
          </p>
        </div>
      )}
    </div>
  );
}
