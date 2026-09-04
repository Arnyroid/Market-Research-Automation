import React, { useEffect, useState } from "react";
import { Plus, BellOff, Bell, Trash2 } from "lucide-react";
import { alertsApi, Alert, CreateAlertPayload } from "../api/alerts";

const CONDITIONS = [
  { value: "price_above",     label: "Price rises above" },
  { value: "price_below",     label: "Price drops below" },
  { value: "pct_change_up",   label: "1-day gain exceeds %" },
  { value: "pct_change_down", label: "1-day drop exceeds %" },
];

function conditionLabel(type: string, threshold: number) {
  const isPct = type.includes("pct");
  const sign  = type === "price_above" || type === "pct_change_up" ? "≥" : "≤";
  return `${CONDITIONS.find(c => c.value === type)?.label ?? type} ${isPct ? `${threshold}%` : `₹${threshold.toLocaleString("en-IN")}` }`;
}

export default function AlertsPage() {
  const [alerts, setAlerts]   = useState<Alert[]>([]);
  const [form, setForm]       = useState({ symbol: "", exchange: "NSE", condition_type: "price_above", threshold: "" });
  const [error, setError]     = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => { alertsApi.list().then(setAlerts).catch(console.error); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.symbol || !form.threshold) return;
    setCreating(true); setError(null);
    try {
      const a = await alertsApi.create({
        symbol: form.symbol.trim().toUpperCase(),
        exchange: form.exchange,
        condition_type: form.condition_type as CreateAlertPayload["condition_type"],
        threshold: parseFloat(form.threshold),
      });
      setAlerts(prev => [a, ...prev]);
      setForm(f => ({ ...f, symbol: "", threshold: "" }));
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

  const active   = alerts.filter(a => a.active);
  const inactive = alerts.filter(a => !a.active);

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Alerts</h1>
        <p className="text-gray-400 text-sm mt-1">Get ntfy push notifications when conditions are met</p>
      </div>

      {/* Create form */}
      <form onSubmit={handleCreate} className="card mb-8">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">New Alert</h2>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Symbol</label>
            <input className="input" placeholder="e.g. RELIANCE" value={form.symbol}
              onChange={e => setForm(f => ({ ...f, symbol: e.target.value }))} />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Exchange</label>
            <select className="select w-full" value={form.exchange}
              onChange={e => setForm(f => ({ ...f, exchange: e.target.value }))}>
              <option>NSE</option><option>BSE</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Condition</label>
            <select className="select w-full" value={form.condition_type}
              onChange={e => setForm(f => ({ ...f, condition_type: e.target.value }))}>
              {CONDITIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">
              Threshold {form.condition_type.includes("pct") ? "(%)" : "(₹)"}
            </label>
            <input className="input" type="number" step="0.01" placeholder="0.00"
              value={form.threshold}
              onChange={e => setForm(f => ({ ...f, threshold: e.target.value }))} />
          </div>
        </div>
        {error && <p className="text-red-400 text-xs mb-3">{error}</p>}
        <button type="submit" disabled={creating} className="btn-primary w-full justify-center">
          <Plus size={15} /> {creating ? "Creating…" : "Create Alert"}
        </button>
      </form>

      {/* Active alerts */}
      {active.length > 0 && (
        <div className="mb-6">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Active <span className="ml-1 bg-blue-600 text-white text-xs px-1.5 py-0.5 rounded-full">{active.length}</span>
          </h2>
          <div className="space-y-2">
            {active.map(a => (
              <div key={a.id} className="card flex items-center justify-between py-3.5">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-600/20 flex items-center justify-center">
                    <Bell size={14} className="text-blue-400" />
                  </div>
                  <div>
                    <span className="font-mono font-semibold text-white text-sm">{a.symbol}</span>
                    <span className="text-xs bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded ml-2">{a.exchange}</span>
                    <p className="text-xs text-gray-400 mt-0.5">{conditionLabel(a.condition_type, a.threshold)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs bg-emerald-900/50 text-emerald-400 px-2 py-0.5 rounded-full font-medium">Active</span>
                  <button onClick={() => toggle(a.id, a.active)} title="Pause" className="btn-ghost p-1.5 hover:text-yellow-400">
                    <BellOff size={15} />
                  </button>
                  <button onClick={() => remove(a.id)} className="btn-ghost p-1.5 hover:text-red-400">
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Inactive alerts */}
      {inactive.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Inactive</h2>
          <div className="space-y-2">
            {inactive.map(a => (
              <div key={a.id} className="card flex items-center justify-between py-3.5 opacity-50">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center">
                    <BellOff size={14} className="text-gray-500" />
                  </div>
                  <div>
                    <span className="font-mono font-semibold text-gray-300 text-sm">{a.symbol}</span>
                    <span className="text-xs bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded ml-2">{a.exchange}</span>
                    <p className="text-xs text-gray-500 mt-0.5">{conditionLabel(a.condition_type, a.threshold)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => toggle(a.id, a.active)} className="text-xs text-blue-400 hover:text-blue-300 transition-colors">Re-enable</button>
                  <button onClick={() => remove(a.id)} className="btn-ghost p-1.5 hover:text-red-400">
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {alerts.length === 0 && (
        <div className="card text-center py-16">
          <Bell size={32} className="text-gray-700 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">No alerts yet — create one above.</p>
          <p className="text-gray-600 text-xs mt-1">You'll get an ntfy push notification when any condition fires.</p>
        </div>
      )}
    </div>
  );
}
