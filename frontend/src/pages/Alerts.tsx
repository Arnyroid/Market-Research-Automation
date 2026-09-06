import React, { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Plus, BellOff, Bell, Trash2, Repeat2, RefreshCw, ChevronDown, ChevronUp, Search } from "lucide-react";
import { alertsApi, Alert, AlertLog, CreateAlertPayload } from "../api/alerts";
import { watchlistApi, SymbolSearchResult } from "../api/watchlist";
import { pricesApi } from "../api/prices";

const CONDITIONS = [
  { value: "price_above",        label: "Price rises above",       unit: "₹" },
  { value: "price_below",        label: "Price drops below",       unit: "₹" },
  { value: "pct_change_up",      label: "1-day gain exceeds",      unit: "%" },
  { value: "pct_change_down",    label: "1-day drop exceeds",      unit: "%" },
  { value: "portfolio_pnl_below", label: "Portfolio P&L drops below", unit: "%" },
];

function conditionLabel(type: string, threshold: number) {
  const c = CONDITIONS.find(x => x.value === type);
  if (!c) return `${type} ${threshold}`;
  return `${c.label} ${c.unit === "%" ? `${threshold}%` : `₹${threshold.toLocaleString("en-IN")}` }`;
}

// ── Alert card ─────────────────────────────────────────────────────────────────

function AlertCard({
  alert,
  onToggle,
  onDelete,
}: {
  alert: Alert;
  onToggle: () => void;
  onDelete: () => void;
}) {
  const [ltp, setLtp]           = useState<number | null>(null);
  const [logs, setLogs]         = useState<AlertLog[]>([]);
  const [showLogs, setShowLogs] = useState(false);

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

  const isPct      = alert.condition_type.includes("pct");
  const isAbove    = alert.condition_type === "price_above" || alert.condition_type === "pct_change_up";
  const distance   = ltp != null && !isPct
    ? ((alert.threshold - ltp) / ltp * 100)
    : null;
  const distLabel  = distance != null
    ? `${Math.abs(distance).toFixed(1)}% ${distance > 0 ? "away ↑" : "away ↓"}`
    : null;

  return (
    <div className={`card p-0 overflow-hidden transition-opacity ${!alert.active ? "opacity-50" : ""}`}>
      <div className="flex items-center justify-between px-4 py-3.5">
        {/* Left: icon + symbol + condition */}
        <div className="flex items-center gap-3 min-w-0">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
            alert.active ? "bg-blue-600/20" : "bg-gray-800"
          }`}>
            {alert.active
              ? <Bell size={14} className="text-blue-400" />
              : <BellOff size={14} className="text-gray-500" />}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono font-semibold text-white text-sm">{alert.symbol}</span>
              <span className="text-xs bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded">{alert.exchange}</span>
              {alert.repeating && (
                <span className="flex items-center gap-1 text-xs text-violet-400 bg-violet-900/30 px-1.5 py-0.5 rounded">
                  <Repeat2 size={11} /> Repeating
                </span>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-0.5">{conditionLabel(alert.condition_type, alert.threshold)}</p>
            {alert.notes && <p className="text-xs text-gray-600 mt-0.5 italic">{alert.notes}</p>}
          </div>
        </div>

        {/* Right: current price + distance + actions */}
        <div className="flex items-center gap-4 shrink-0 ml-4">
          {ltp != null && (
            <div className="text-right hidden sm:block">
              <p className="font-mono text-sm text-white">₹{ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</p>
              {distLabel && <p className={`text-xs mt-0.5 ${isAbove ? "text-emerald-500" : "text-red-500"}`}>{distLabel}</p>}
            </div>
          )}
          <div className="flex items-center gap-1">
            <button
              onClick={toggleLogs}
              title="Trigger history"
              className="btn-ghost p-1.5 hover:text-blue-400"
            >
              {showLogs ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </button>
            <button
              onClick={onToggle}
              title={alert.active ? "Pause" : "Re-enable"}
              className={`btn-ghost p-1.5 ${alert.active ? "hover:text-yellow-400" : "hover:text-emerald-400"}`}
            >
              {alert.active ? <BellOff size={15} /> : <Bell size={15} />}
            </button>
            <button onClick={onDelete} className="btn-ghost p-1.5 hover:text-red-400">
              <Trash2 size={15} />
            </button>
          </div>
        </div>
      </div>

      {/* Trigger log */}
      {showLogs && (
        <div className="border-t border-gray-800 px-4 py-3">
          {logs.length === 0
            ? <p className="text-xs text-gray-600 text-center py-2">No triggers yet.</p>
            : (
              <div className="space-y-1.5">
                {logs.slice(0, 5).map(l => (
                  <div key={l.id} className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">{new Date(l.triggered_at).toLocaleString("en-IN")}</span>
                    <span className="font-mono text-gray-300">₹{l.price_at_trigger.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                    <span className={l.notified ? "text-emerald-500" : "text-gray-600"}>
                      {l.notified ? "Notified ✓" : "Not sent"}
                    </span>
                  </div>
                ))}
              </div>
            )
          }
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

  // Form state — initialise from URL params when navigated from StockDetail
  const prefillSymbol   = sp.get("symbol")?.toUpperCase() ?? "";
  const prefillExchange = sp.get("exchange")?.toUpperCase() ?? "NSE";

  const [query, setQuery]           = useState(prefillSymbol);
  const [selSymbol, setSelSymbol]   = useState(prefillSymbol);
  const [selExchange, setSelExchange] = useState(prefillExchange);
  const [suggestions, setSuggestions] = useState<SymbolSearchResult[]>([]);
  const [showSug, setShowSug]       = useState(false);
  const [condition, setCondition]   = useState("price_above");
  const [threshold, setThreshold]   = useState("");
  const [repeating, setRepeating]   = useState(false);
  const [notes, setNotes]           = useState("");
  const [fetchingPrice, setFetchingPrice] = useState(false);

  const debounce  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dropRef   = useRef<HTMLDivElement>(null);

  useEffect(() => {
    alertsApi.list().then(setAlerts).catch(console.error);
  }, []);

  // When navigated from StockDetail, auto-fetch current price for the pre-filled symbol
  useEffect(() => {
    if (!prefillSymbol) return;
    setFetchingPrice(true);
    pricesApi.getQuote(prefillSymbol, prefillExchange)
      .then(q => { if (q?.ltp) setThreshold(q.ltp.toFixed(2)); })
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
    setQuery(v); setSelSymbol("");
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

    // Pre-fill threshold with current price for price-type conditions
    if (!condition.includes("pct")) {
      setFetchingPrice(true);
      try {
        const q = await pricesApi.getQuote(s.symbol, s.exchange);
        if (q?.ltp) setThreshold(q.ltp.toFixed(2));
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
        symbol: sym,
        exchange: selExchange,
        condition_type: condition as CreateAlertPayload["condition_type"],
        threshold: parseFloat(threshold),
        repeating,
        notes: notes || undefined,
      } as any);
      setAlerts(prev => [a, ...prev]);
      setQuery(""); setSelSymbol(""); setThreshold(""); setNotes(""); setRepeating(false);
    } catch (err: any) { setError(err.message); }
    finally { setCreating(false); }
  }

  async function toggle(id: number, active: boolean) {
    const a = await alertsApi.update(id, { active: !active });
    setAlerts(prev => prev.map(x => x.id === id ? a : x));
  }

  async function remove(id: number) {
    await alertsApi.remove(id);
    setAlerts(prev => prev.filter(x => x.id !== id));
  }

  const allActive   = alerts.filter(a => a.active);
  const allInactive = alerts.filter(a => !a.active);
  const unit        = CONDITIONS.find(c => c.value === condition)?.unit ?? "₹";

  const filterFn = (a: Alert) => {
    if (!alertFilter.trim()) return true;
    const q = alertFilter.trim().toLowerCase();
    return (
      a.symbol.toLowerCase().includes(q) ||
      (a.notes ?? "").toLowerCase().includes(q) ||
      a.condition_type.toLowerCase().includes(q)
    );
  };
  const active   = allActive.filter(filterFn);
  const inactive = allInactive.filter(filterFn);

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Alerts</h1>
          <p className="text-gray-400 text-sm mt-1">Get ntfy push notifications when conditions are met</p>
        </div>
        {alerts.length > 1 && (
          <div className="relative mt-1">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              className="input pl-8 text-sm py-2 w-52"
              placeholder="Filter alerts…"
              value={alertFilter}
              onChange={e => setAlertFilter(e.target.value)}
            />
          </div>
        )}
      </div>

      {/* Create form */}
      <form onSubmit={handleCreate} className="card mb-8 space-y-4">
        <h2 className="text-sm font-semibold text-gray-300">New Alert</h2>

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

        {/* Condition + Exchange */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Condition</label>
            <select className="select w-full" value={condition}
              onChange={e => { setCondition(e.target.value); setThreshold(""); }}>
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

        {/* Threshold */}
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">
            Threshold ({unit === "%" ? "%" : "₹"})
            {fetchingPrice && <span className="ml-1 text-gray-600 text-xs">fetching current price…</span>}
          </label>
          <input className={`input ${fetchingPrice ? "opacity-50" : ""}`}
            type="number" step="0.01" min="0" placeholder={unit === "%" ? "5.0" : "1300.00"}
            value={threshold} onChange={e => setThreshold(e.target.value)}
            disabled={fetchingPrice} />
        </div>

        {/* Notes */}
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Notes <span className="text-gray-600">(optional)</span></label>
          <input className="input" placeholder="e.g. earnings breakout, support level…"
            value={notes} onChange={e => setNotes(e.target.value)} />
        </div>

        {/* Repeating toggle */}
        <label className="flex items-center gap-3 cursor-pointer select-none">
          <div
            onClick={() => setRepeating(v => !v)}
            className={`w-9 h-5 rounded-full transition-colors relative ${repeating ? "bg-violet-600" : "bg-gray-700"}`}
          >
            <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${repeating ? "translate-x-4" : "translate-x-0.5"}`} />
          </div>
          <span className="text-sm text-gray-300">Repeating alert</span>
          <span className="text-xs text-gray-600">(fires every poll cycle while condition holds; default fires once then pauses)</span>
        </label>

        {error && <p className="text-red-400 text-xs bg-red-900/20 rounded px-3 py-2">{error}</p>}

        <button type="submit" disabled={creating} className="btn-primary w-full justify-center">
          <Plus size={15} /> {creating ? "Creating…" : "Create Alert"}
        </button>
      </form>

      {/* Active alerts */}
      {allActive.length > 0 && (
        <div className="mb-6">
          <h2 className="flex items-center gap-2 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Active
            <span className="bg-blue-600 text-white text-xs px-1.5 py-0.5 rounded-full font-normal">{allActive.length}</span>
          </h2>
          {active.length === 0 && alertFilter && (
            <p className="text-xs text-gray-600 py-2">No active alerts match your filter.</p>
          )}
          <div className="space-y-2">
            {active.map(a => (
              <AlertCard key={a.id} alert={a}
                onToggle={() => toggle(a.id, a.active)}
                onDelete={() => remove(a.id)} />
            ))}
          </div>
        </div>
      )}

      {/* Inactive alerts */}
      {allInactive.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Paused / Fired</h2>
          {inactive.length === 0 && alertFilter && (
            <p className="text-xs text-gray-600 py-2">No paused alerts match your filter.</p>
          )}
          <div className="space-y-2">
            {inactive.map(a => (
              <AlertCard key={a.id} alert={a}
                onToggle={() => toggle(a.id, a.active)}
                onDelete={() => remove(a.id)} />
            ))}
          </div>
        </div>
      )}

      {alerts.length === 0 && (
        <div className="card text-center py-16">
          <Bell size={32} className="text-gray-700 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">No alerts yet — create one above.</p>
          <p className="text-gray-600 text-xs mt-1">ntfy push notifications fire when any condition is met.</p>
        </div>
      )}
    </div>
  );
}
