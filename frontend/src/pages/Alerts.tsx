import React, { useEffect, useState } from "react";
import { Plus, BellOff } from "lucide-react";
import { alertsApi, Alert, CreateAlertPayload } from "../api/alerts";

const CONDITION_LABELS: Record<string, string> = {
  price_above:     "Price ≥",
  price_below:     "Price ≤",
  pct_change_up:   "1-day gain ≥",
  pct_change_down: "1-day drop ≥",
};

export default function AlertsPage() {
  const [alerts, setAlerts]       = useState<Alert[]>([]);
  const [form, setForm]           = useState<Omit<CreateAlertPayload, "notes">>({
    symbol: "", exchange: "NSE", condition_type: "price_above", threshold: 0,
  });
  const [error, setError]         = useState<string | null>(null);

  useEffect(() => {
    alertsApi.list().then(setAlerts).catch(console.error);
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const a = await alertsApi.create({ ...form, symbol: form.symbol.toUpperCase() });
      setAlerts((prev) => [a, ...prev]);
      setForm((f) => ({ ...f, symbol: "", threshold: 0 }));
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleDeactivate(id: number) {
    await alertsApi.update(id, { active: false });
    setAlerts((prev) => prev.map((a) => a.id === id ? { ...a, active: false } : a));
  }

  async function handleDelete(id: number) {
    await alertsApi.remove(id);
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Alerts</h1>

      <form onSubmit={handleCreate} className="grid grid-cols-2 gap-3 mb-6 p-4 bg-gray-50 rounded-lg">
        <input className="border rounded px-3 py-2 text-sm col-span-2" placeholder="Symbol"
          value={form.symbol} onChange={(e) => setForm((f) => ({ ...f, symbol: e.target.value }))} />

        <select className="border rounded px-3 py-2 text-sm" value={form.exchange}
          onChange={(e) => setForm((f) => ({ ...f, exchange: e.target.value }))}>
          <option>NSE</option><option>BSE</option>
        </select>

        <select className="border rounded px-3 py-2 text-sm" value={form.condition_type}
          onChange={(e) => setForm((f) => ({ ...f, condition_type: e.target.value as CreateAlertPayload["condition_type"] }))}>
          {Object.entries(CONDITION_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>

        <input type="number" step="0.01" className="border rounded px-3 py-2 text-sm col-span-2"
          placeholder="Threshold (₹ or %)" value={form.threshold || ""}
          onChange={(e) => setForm((f) => ({ ...f, threshold: parseFloat(e.target.value) }))} />

        <button type="submit"
          className="col-span-2 bg-blue-600 text-white py-2 rounded text-sm flex items-center justify-center gap-2 hover:bg-blue-700">
          <Plus size={16} /> Create Alert
        </button>
      </form>

      {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

      <div className="space-y-2">
        {alerts.map((a) => (
          <div key={a.id} className={`flex items-center justify-between p-4 rounded-lg border ${a.active ? "bg-white" : "bg-gray-50 opacity-60"}`}>
            <div>
              <span className="font-mono font-semibold">{a.symbol}</span>
              <span className="text-gray-400 text-xs ml-2">{a.exchange}</span>
              <p className="text-sm text-gray-600 mt-0.5">
                {CONDITION_LABELS[a.condition_type]} {a.condition_type.includes("pct") ? `${a.threshold}%` : `₹${a.threshold.toLocaleString("en-IN")}`}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${a.active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                {a.active ? "Active" : "Inactive"}
              </span>
              {a.active && (
                <button onClick={() => handleDeactivate(a.id)} title="Deactivate" className="text-gray-400 hover:text-orange-500">
                  <BellOff size={16} />
                </button>
              )}
              <button onClick={() => handleDelete(a.id)} className="text-gray-400 hover:text-red-500 text-xs">✕</button>
            </div>
          </div>
        ))}
        {alerts.length === 0 && <p className="text-gray-400 text-center py-8">No alerts set.</p>}
      </div>
    </div>
  );
}
