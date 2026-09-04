import React, { useEffect, useState } from "react";
import { Plus, Trash2, TrendingUp, TrendingDown } from "lucide-react";
import { watchlistApi, WatchlistItem } from "../api/watchlist";
import { usePriceSocket } from "../hooks/usePriceSocket";
import clsx from "clsx";

export default function WatchlistPage() {
  const [items, setItems]         = useState<WatchlistItem[]>([]);
  const [symbol, setSymbol]       = useState("");
  const [exchange, setExchange]   = useState<"NSE" | "BSE">("NSE");
  const [adding, setAdding]       = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const livePrices                = usePriceSocket();

  useEffect(() => {
    watchlistApi.list().then(setItems).catch(console.error);
  }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!symbol.trim()) return;
    setAdding(true);
    setError(null);
    try {
      const item = await watchlistApi.add({ symbol: symbol.trim().toUpperCase(), exchange });
      setItems((prev) => [item, ...prev]);
      setSymbol("");
    } catch (err: any) {
      setError(err.message ?? "Failed to add symbol");
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(id: number) {
    await watchlistApi.remove(id);
    setItems((prev) => prev.filter((i) => i.id !== id));
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Watchlist</h1>

      {/* Add form */}
      <form onSubmit={handleAdd} className="flex gap-3 mb-6">
        <input
          className="border rounded px-3 py-2 flex-1 text-sm"
          placeholder="Symbol (e.g. RELIANCE or 500325)"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
        />
        <select
          className="border rounded px-3 py-2 text-sm"
          value={exchange}
          onChange={(e) => setExchange(e.target.value as "NSE" | "BSE")}
        >
          <option>NSE</option>
          <option>BSE</option>
        </select>
        <button
          type="submit"
          disabled={adding}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm flex items-center gap-2 hover:bg-blue-700 disabled:opacity-50"
        >
          <Plus size={16} /> Add
        </button>
      </form>

      {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

      {/* Table */}
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-gray-50 text-left">
            <th className="px-4 py-2 border-b">Symbol</th>
            <th className="px-4 py-2 border-b">Exchange</th>
            <th className="px-4 py-2 border-b">Company</th>
            <th className="px-4 py-2 border-b text-right">LTP</th>
            <th className="px-4 py-2 border-b text-right">Change</th>
            <th className="px-4 py-2 border-b"></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const live = livePrices.get(`${item.symbol}:${item.exchange}`);
            const pct  = live?.pct_change ?? null;
            return (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 border-b font-mono font-semibold">{item.symbol}</td>
                <td className="px-4 py-3 border-b text-gray-500">{item.exchange}</td>
                <td className="px-4 py-3 border-b text-gray-700">{item.company_name ?? "—"}</td>
                <td className="px-4 py-3 border-b text-right font-mono">
                  {live ? `₹${live.ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "—"}
                </td>
                <td className={clsx("px-4 py-3 border-b text-right flex items-center justify-end gap-1",
                  pct == null ? "text-gray-400" : pct >= 0 ? "text-green-600" : "text-red-600")}>
                  {pct != null && (pct >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />)}
                  {pct != null ? `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%` : "—"}
                </td>
                <td className="px-4 py-3 border-b text-right">
                  <button onClick={() => handleRemove(item.id)} className="text-gray-400 hover:text-red-500">
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            );
          })}
          {items.length === 0 && (
            <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No symbols yet — add one above.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
