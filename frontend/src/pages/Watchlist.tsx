import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Trash2, TrendingUp, TrendingDown, Search } from "lucide-react";
import { watchlistApi, WatchlistItem } from "../api/watchlist";
import { pricesApi, Quote } from "../api/prices";
import { usePriceSocket } from "../hooks/usePriceSocket";

export default function WatchlistPage() {
  const [items, setItems]           = useState<WatchlistItem[]>([]);
  const [restPrices, setRestPrices] = useState<Map<string, Quote>>(new Map());
  const [symbol, setSymbol]         = useState("");
  const [exchange, setExchange]     = useState<"NSE" | "BSE">("NSE");
  const [adding, setAdding]         = useState(false);
  const [error, setError]           = useState<string | null>(null);
  const livePrices                  = usePriceSocket();
  const navigate                    = useNavigate();

  useEffect(() => {
    watchlistApi.list().then(loaded => {
      setItems(loaded);
      // Immediately fetch prices for all symbols so the table isn't blank
      // while waiting for the first 60s WebSocket push.
      loaded.forEach(item => {
        pricesApi.getQuote(item.symbol, item.exchange)
          .then(q => setRestPrices(prev => {
            const next = new Map(prev);
            next.set(`${item.symbol}:${item.exchange}`, q);
            return next;
          }))
          .catch(() => {/* ignore individual quote failures */});
      });
    }).catch(console.error);
  }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!symbol.trim()) return;
    setAdding(true); setError(null);
    try {
      const item = await watchlistApi.add({
        symbol: symbol.trim().toUpperCase(),
        exchange,
      });
      setItems(prev => [item, ...prev]);
      setSymbol("");
    } catch (err: any) {
      setError(err.message ?? "Failed to add symbol");
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(e: React.MouseEvent, id: number) {
    e.stopPropagation();
    await watchlistApi.remove(id);
    setItems(prev => prev.filter(i => i.id !== id));
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Watchlist</h1>
        <p className="text-gray-400 text-sm mt-1">Track NSE &amp; BSE equities with live prices</p>
      </div>

      {/* Add form */}
      <form onSubmit={handleAdd} className="card flex gap-3 mb-6 items-end">
        <div className="flex-1">
          <label className="block text-xs text-gray-400 mb-1.5">Symbol</label>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              className="input pl-8"
              placeholder="e.g. RELIANCE or 500325"
              value={symbol}
              onChange={e => setSymbol(e.target.value)}
            />
          </div>
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

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-800/50">
            <tr>
              <th className="th">Symbol</th>
              <th className="th">Exchange</th>
              <th className="th">Company</th>
              <th className="th text-right">LTP</th>
              <th className="th text-right">Change</th>
              <th className="th text-right">1D %</th>
              <th className="th w-10"></th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={7} className="td text-center text-gray-500 py-16">
                  No symbols yet — add one above to get started.
                </td>
              </tr>
            )}
            {items.map(item => {
              const key  = `${item.symbol}:${item.exchange}`;
              // WebSocket prices take priority once they arrive; REST prices fill
              // the table immediately on first load.
              const live = livePrices.get(key) ?? restPrices.get(key) ?? null;
              const pct  = live?.pct_change ?? null;
              const isUp = pct != null && pct >= 0;
              return (
                <tr
                  key={item.id}
                  onClick={() => navigate(`/stock/${item.symbol}?exchange=${item.exchange}`)}
                  className="hover:bg-gray-800/40 cursor-pointer transition-colors"
                >
                  <td className="td font-mono font-semibold text-white">{item.symbol}</td>
                  <td className="td">
                    <span className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded font-medium">{item.exchange}</span>
                  </td>
                  <td className="td text-gray-300">{item.company_name ?? <span className="text-gray-600">—</span>}</td>
                  <td className="td text-right font-mono text-white">
                    {live ? `₹${live.ltp.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : <span className="text-gray-600">—</span>}
                  </td>
                  <td className={`td text-right font-mono ${live && pct != null ? (isUp ? "gain" : "loss") : "text-gray-600"}`}>
                    {live && pct != null
                      ? `${isUp ? "+" : ""}₹${((live.ltp - (live.ltp / (1 + pct / 100))).toFixed(2))}`
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
                      className="text-gray-600 hover:text-red-400 transition-colors"
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
        <p className="text-xs text-gray-600 mt-3 text-right">
          Live prices update every 60s during market hours · Click a row to view details
        </p>
      )}
    </div>
  );
}
